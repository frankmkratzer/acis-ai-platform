#!/usr/bin/env python3
"""
Model Management CLI Tool

Manages ML model versions, production promotions, and safe deletions.

Usage:
    python scripts/manage_models.py list                      # List all models
    python scripts/manage_models.py list --production         # List production models
    python scripts/manage_models.py promote MODEL_NAME        # Promote to production
    python scripts/manage_models.py delete MODEL_NAME         # Delete model (if not prod)
    python scripts/manage_models.py status MODEL_NAME         # Get model details
"""
import argparse
import sys
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from tabulate import tabulate

DB_CONFIG = {
    "host": "localhost",
    "database": "acis-ai",
    "user": "postgres",
    "password": "$@nJose420",
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def list_models(production_only=False):
    """List all models or only production models"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT
            model_name,
            version,
            framework,
            status,
            is_production,
            spearman_ic,
            trained_at,
            size_mb
        FROM model_versions
        WHERE status != 'deleted'
    """

    if production_only:
        query += " AND is_production = TRUE"

    query += " ORDER BY trained_at DESC"

    cursor.execute(query)
    models = cursor.fetchall()

    if not models:
        print("No models found.")
        return

    # Format for display
    headers = [
        "Model",
        "Version",
        "Framework",
        "Status",
        "Prod",
        "Spearman IC",
        "Trained At",
        "Size (MB)",
    ]
    rows = []

    for m in models:
        rows.append(
            [
                m["model_name"],
                m["version"],
                m["framework"],
                m["status"],
                "✓" if m["is_production"] else "",
                f"{m['spearman_ic']:.4f}" if m["spearman_ic"] else "N/A",
                m["trained_at"].strftime("%Y-%m-%d %H:%M") if m["trained_at"] else "N/A",
                f"{m['size_mb']:.2f}" if m["size_mb"] else "N/A",
            ]
        )

    print("\n" + tabulate(rows, headers=headers, tablefmt="grid"))
    print(f"\nTotal: {len(models)} models")

    conn.close()


def get_model_status(model_name):
    """Get detailed status of a specific model"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT *
        FROM model_versions
        WHERE model_name = %s
        ORDER BY trained_at DESC
        LIMIT 1
    """,
        (model_name,),
    )

    model = cursor.fetchone()

    if not model:
        print(f"Model '{model_name}' not found.")
        return

    print(f"\n{'='*60}")
    print(f"Model: {model['model_name']}")
    print(f"{'='*60}")
    print(f"Version:              {model['version']}")
    print(f"Framework:            {model['framework']}")
    print(f"Status:               {model['status']}")
    print(f"Production:           {'✓ YES' if model['is_production'] else 'No'}")
    print(f"Trained At:           {model['trained_at']}")
    if model["promoted_to_production_at"]:
        print(f"Promoted At:          {model['promoted_to_production_at']}")
    print(f"Model Path:           {model['model_path']}")
    print(f"Size:                 {model['size_mb']} MB" if model["size_mb"] else "Size: N/A")
    print(f"\nPerformance Metrics:")
    print(
        f"  Spearman IC:        {model['spearman_ic']}"
        if model["spearman_ic"]
        else "  Spearman IC: N/A"
    )
    print(
        f"  Pearson Corr:       {model['pearson_correlation']}"
        if model["pearson_correlation"]
        else "  Pearson Corr: N/A"
    )

    if model["description"]:
        print(f"\nDescription:")
        print(f"  {model['description']}")

    if model["notes"]:
        print(f"\nNotes:")
        print(f"  {model['notes']}")

    # Get deployment history
    cursor.execute(
        """
        SELECT action, previous_status, new_status, performed_by, performed_at, reason
        FROM model_deployment_log
        WHERE model_version_id = %s
        ORDER BY performed_at DESC
        LIMIT 10
    """,
        (model["id"],),
    )

    history = cursor.fetchall()

    if history:
        print(f"\n{'='*60}")
        print("Recent Deployment History:")
        print(f"{'='*60}")
        for h in history:
            print(f"  [{h['performed_at'].strftime('%Y-%m-%d %H:%M')}] {h['action'].upper()}")
            print(f"    {h['previous_status']} → {h['new_status']}")
            if h["reason"]:
                print(f"    Reason: {h['reason']}")
            print()

    conn.close()


def promote_model(model_name, reason=None):
    """Promote a model to production"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Check if model exists
    cursor.execute(
        """
        SELECT id, framework, status, is_production
        FROM model_versions
        WHERE model_name = %s
        ORDER BY trained_at DESC
        LIMIT 1
    """,
        (model_name,),
    )

    model = cursor.fetchone()

    if not model:
        print(f"Error: Model '{model_name}' not found.")
        return False

    if model["is_production"]:
        print(f"Model '{model_name}' is already in production.")
        return True

    # Get current production model for this framework
    cursor.execute(
        """
        SELECT model_name
        FROM model_versions
        WHERE framework = %s AND is_production = TRUE
    """,
        (model["framework"],),
    )

    current_prod = cursor.fetchone()

    if current_prod:
        print(f"\nCurrent production model for {model['framework']}: {current_prod['model_name']}")
        confirm = input(f"Replace with '{model_name}'? (yes/no): ")
        if confirm.lower() not in ["yes", "y"]:
            print("Promotion cancelled.")
            return False

    # Promote
    cursor.execute(
        """
        SELECT promote_model_to_production(%s, %s, %s)
    """,
        (model["id"], "cli_user", reason or "Promoted via CLI"),
    )

    conn.commit()

    print(f"\n✓ Model '{model_name}' promoted to production!")
    print(f"  Framework: {model['framework']}")

    conn.close()
    return True


def delete_model(model_name, force=False):
    """Delete a model (with safety checks)"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Check if model exists and is production
    cursor.execute(
        """
        SELECT id, is_production, status
        FROM model_versions
        WHERE model_name = %s
        ORDER BY trained_at DESC
        LIMIT 1
    """,
        (model_name,),
    )

    model = cursor.fetchone()

    if not model:
        print(f"Error: Model '{model_name}' not found.")
        return False

    if model["is_production"] and not force:
        print(f"Error: Cannot delete production model '{model_name}'.")
        print("Please promote a different model to production first, or use --force (dangerous!).")
        return False

    # Confirm deletion
    if not force:
        confirm = input(f"Delete model '{model_name}'? This cannot be undone. (yes/no): ")
        if confirm.lower() not in ["yes", "y"]:
            print("Deletion cancelled.")
            return False

    # Mark as deleted
    cursor.execute(
        """
        UPDATE model_versions
        SET status = 'deleted'
        WHERE model_name = %s
    """,
        (model_name,),
    )

    # Log deletion
    cursor.execute(
        """
        INSERT INTO model_deployment_log (
            model_version_id, action, previous_status, new_status,
            performed_by, reason
        ) VALUES (%s, 'deleted', %s, 'deleted', 'cli_user', 'Deleted via CLI')
    """,
        (model["id"], model["status"]),
    )

    conn.commit()

    print(f"\n✓ Model '{model_name}' marked as deleted in database.")
    print("  Note: Filesystem files not removed. Use manual cleanup if needed.")

    conn.close()
    return True


def main():
    parser = argparse.ArgumentParser(description="ML Model Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    list_parser = subparsers.add_parser("list", help="List models")
    list_parser.add_argument(
        "--production", action="store_true", help="Only show production models"
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Get model status")
    status_parser.add_argument("model_name", help="Name of the model")

    # Promote command
    promote_parser = subparsers.add_parser("promote", help="Promote model to production")
    promote_parser.add_argument("model_name", help="Name of the model")
    promote_parser.add_argument("--reason", help="Reason for promotion")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete model")
    delete_parser.add_argument("model_name", help="Name of the model")
    delete_parser.add_argument(
        "--force", action="store_true", help="Force delete even if production"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "list":
            list_models(production_only=args.production)
        elif args.command == "status":
            get_model_status(args.model_name)
        elif args.command == "promote":
            promote_model(args.model_name, args.reason)
        elif args.command == "delete":
            delete_model(args.model_name, args.force)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

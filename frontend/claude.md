# Frontend Directory - Next.js 14 Web Application

## Purpose
Next.js 14 application with App Router, providing the user interface for ACIS AI platform.

## Structure
```
frontend/src/
├── app/                    # App Router pages
│   ├── page.tsx           # Dashboard home
│   ├── clients/           # Client management
│   ├── trading/           # Trading interface
│   ├── ml-models/         # Model management
│   ├── brokerages/        # Brokerage connections
│   └── docs/              # Documentation pages
├── components/            # Reusable React components
├── lib/                   # Utilities and API client
└── types/                 # TypeScript type definitions
```

## Key Technologies
- **Next.js 14**: App Router, Server Components
- **TypeScript**: Type safety
- **Tailwind CSS**: Utility-first styling
- **Lucide React**: Icon library

## API Client
See `lib/api.ts` for REST API integration with backend (port 8000).

## Development
```bash
npm run dev  # Start dev server on port 3000
npm run build
npm run start
```

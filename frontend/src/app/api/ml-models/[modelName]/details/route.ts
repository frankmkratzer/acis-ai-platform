import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: { modelName: string } }
) {
  try {
    const modelName = params.modelName;

    const response = await fetch(`http://localhost:8000/api/ml-models/${modelName}/details`);
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching model details:', error);
    return NextResponse.json(
      { error: 'Failed to fetch model details' },
      { status: 500 }
    );
  }
}

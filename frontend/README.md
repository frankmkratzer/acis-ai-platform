# ACIS AI Platform - Frontend

Next.js + TypeScript + TailwindCSS frontend for the AI wealth management platform.

## Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

Create `.env.local` (already created):
```
NEXT_PUBLIC_API_URL=http://192.168.50.234:8000
```

### 3. Run Development Server

```bash
npm run dev
```

Frontend will be available at: http://localhost:3000

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js 14 App Router
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Dashboard home
│   │   ├── clients/            # Client pages
│   │   ├── portfolios/         # Portfolio pages
│   │   └── trading/            # Trading pages
│   ├── components/             # React components
│   │   ├── Navigation.tsx
│   │   ├── ClientList.tsx
│   │   ├── PortfolioView.tsx
│   │   └── TradeRecommendations.tsx
│   ├── lib/                    # Utilities
│   │   └── api.ts              # API client
│   └── types/                  # TypeScript types
│       └── index.ts
├── public/                     # Static files
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.js
```

## Pages to Build

### 1. Dashboard (/)
- Welcome message
- Quick stats (clients, accounts, portfolios)
- Recent activity
- Links to main sections

### 2. Clients (/clients)
- List all clients
- Search/filter
- Add new client
- View client details

### 3. Client Detail (/clients/[id])
- Client information
- Connected brokerage accounts
- Portfolio overview
- Recent trades

### 4. Portfolio View (/portfolios/[clientId])
- Current positions table
- Portfolio allocation pie chart
- Performance metrics
- Cash balance

### 5. Trading (/trading)
- Generate recommendations button
- List of recommendations (pending, approved)
- Recommendation details with trades
- Approve/reject buttons
- Execute trades button

### 6. Trade History (/trading/history)
- Table of executed trades
- Filter by client, date, status
- Export to CSV

## API Client

The API client (`src/lib/api.ts`) provides type-safe functions for all backend endpoints:

```typescript
// Example usage
import api from '@/lib/api'

// Get clients
const clients = await api.clients.list()

// Get portfolio
const portfolio = await api.schwab.getPortfolio(clientId, accountHash)

// Generate recommendations
const recommendations = await api.trading.generateRecommendations({
  client_id: 1,
  account_hash: 'ABC123',
  portfolio_id: 1
})
```

## Components

### Navigation
- Top navigation bar
- Links to main sections
- User info (admin)

### ClientList
- Table of clients
- Click to view details

### PortfolioView
- Positions table
- Allocation chart (pie/donut)
- Performance metrics

### TradeRecommendations
- List of recommendations
- Expandable trade details
- Approve/reject actions
- Execute button

## Styling

Uses TailwindCSS for styling:
- Responsive design
- Clean, professional look
- Blue color scheme (matches financial theme)

## Authentication

Simple authentication for now:
- Login page
- HTTP Basic Auth to backend
- Store credentials in session/localStorage

## Next Steps

1. **Install dependencies**: `npm install`
2. **Create API client**: `src/lib/api.ts`
3. **Create TypeScript types**: `src/types/index.ts`
4. **Build layout**: `src/app/layout.tsx`
5. **Build dashboard**: `src/app/page.tsx`
6. **Build client pages**: `src/app/clients/`
7. **Build portfolio pages**: `src/app/portfolios/`
8. **Build trading pages**: `src/app/trading/`
9. **Test**: http://localhost:3000

## Notes

- Backend must be running at http://192.168.50.234:8000
- Use backend API docs for reference: http://192.168.50.234:8000/api/docs
- All API calls use HTTP Basic Auth with `admin@acis-ai.com` / `admin123`

## Development Tips

- Use `npm run dev` for hot reload
- Check browser console for errors
- Use React DevTools for debugging
- Test with real backend data

## Production Build

```bash
npm run build
npm start
```

Production will run on port 3000.

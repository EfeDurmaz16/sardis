# Sardis Mobile Companion App

Mobile companion app for Sardis - the Payment OS for the Agent Economy. Manage AI agent spending, approve transactions, and monitor alerts on the go.

## Features

- **Dashboard**: Real-time agent spending overview with budget utilization
- **Alerts**: Push notifications for policy violations and suspicious activity
- **Approvals**: Swipe-to-approve interface for pending transactions
- **Policies**: Quick policy management with toggle controls
- **Reports**: Visual spending analytics with export functionality

## Prerequisites

- Node.js 18+ and npm 9+
- Expo CLI: `npm install -g expo-cli`
- iOS Simulator (Mac only) or Android Emulator
- Sardis API key

## Installation

```bash
# Install dependencies
npm install

# Start development server
npm start
```

## Development

### Running on iOS Simulator

```bash
npm run ios
```

### Running on Android Emulator

```bash
npm run android
```

### Running on Physical Device

1. Install Expo Go app on your device
2. Run `npm start`
3. Scan QR code with Expo Go (Android) or Camera app (iOS)

## Configuration

### API Setup

1. Open the app
2. Navigate to Settings
3. Enter your Sardis API key
4. (Optional) Configure custom API base URL

API credentials are stored securely using Expo SecureStore.

### Environment Variables

Create `.env` file (optional):

```bash
SARDIS_API_URL=https://api.sardis.sh/api/v2
```

## Architecture

### Project Structure

```
mobile/
├── src/
│   ├── api/              # API client
│   ├── contexts/         # React contexts (auth, theme)
│   ├── screens/          # Screen components
│   ├── theme/            # Colors and styling
│   └── types/            # TypeScript types
├── assets/               # Images and icons
├── App.tsx               # App entry point
└── package.json
```

### Tech Stack

- **Framework**: React Native + Expo
- **Navigation**: React Navigation (tabs + stack)
- **State**: React Context API + hooks
- **Storage**: Expo SecureStore (encrypted)
- **API**: Fetch API with custom client
- **Styling**: StyleSheet.create (no external CSS)

### Key Components

- **AuthContext**: API key management with SecureStore
- **TabNavigator**: Bottom tab navigation (5 tabs)
- **API Client**: Type-safe Sardis API wrapper
- **Theme System**: Centralized color palette

## Screens

### Dashboard
- Total spending overview (30-day rolling)
- Active agents list with status badges
- Budget utilization progress bars
- Quick stats (agents, cards, blocks)

### Alerts
- Real-time alert feed
- Filter by severity (info/warning/critical)
- Pull-to-refresh
- Tap to mark as read

### Approvals
- Pending approval requests list
- Swipe gestures for approve/reject
- Transaction detail modal
- Policy violation warnings

### Policies
- Active spending policies
- Quick enable/disable toggle
- Policy limits display
- Allowed/blocked categories

### Reports
- Period selector (7d/30d/90d)
- Agent & category breakdowns
- Daily spending chart
- CSV export with share sheet

## Security

- API keys stored in encrypted SecureStore
- HTTPS-only API communication
- No credentials in source code
- Automatic token refresh (future)

## Styling Guidelines

- Deep purple primary (#7C3AED)
- Amber accent (#F59E0B)
- Professional enterprise aesthetic
- Consistent 16px padding
- 12px border radius for cards
- Shadow depth for elevation

## Testing

```bash
# Run tests
npm test

# Type checking
npm run type-check

# Linting
npm run lint
```

## Building for Production

### iOS (TestFlight)

```bash
# Configure app.json with bundle identifier
eas build --platform ios
```

### Android (Google Play)

```bash
# Configure app.json with package name
eas build --platform android
```

## Screenshots

*Coming soon*

## API Integration

The app integrates with Sardis API v2 endpoints:

- `GET /agents` - List agents
- `GET /alerts` - Fetch alerts
- `POST /alerts/{id}/read` - Mark alert as read
- `GET /approvals` - Pending approvals
- `POST /approvals/{id}/approve` - Approve transaction
- `POST /approvals/{id}/reject` - Reject transaction
- `GET /policies` - List policies
- `PATCH /policies/{id}` - Update policy
- `GET /reports/spending` - Spending summary
- `GET /stats/quick` - Quick stats

## Roadmap

- [ ] Biometric authentication (Face ID / Touch ID)
- [ ] Push notifications via FCM/APNs
- [ ] Offline mode with sync
- [ ] Multi-account support
- [ ] Transaction search
- [ ] Custom date range reports
- [ ] Dark mode support
- [ ] Widgets (iOS 14+)

## Support

For issues or questions:
- GitHub Issues: https://github.com/sardis/sardis/issues
- Docs: https://sardis.sh/docs
- Email: support@sardis.sh

## License

MIT License - see LICENSE file for details

---

**Sardis** - AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust.

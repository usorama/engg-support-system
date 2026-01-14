# ESS Chat - iPhone Installation Guide

Install ESS Chat as a native app on your iPhone for the best experience.

## Prerequisites

- iPhone running iOS 11.3 or later
- Safari browser (required for PWA installation)
- Internet connection

## Installation Steps

### Step 1: Open ESS Chat in Safari

1. Open **Safari** on your iPhone
2. Navigate to: **https://ess.ping-gadgets.com**
3. Wait for the page to fully load

> **Important**: You must use Safari. PWA installation is not supported in Chrome, Firefox, or other browsers on iOS.

### Step 2: Add to Home Screen

1. Tap the **Share** button (box with arrow pointing up) at the bottom of Safari
2. Scroll down and tap **"Add to Home Screen"**
3. (Optional) Edit the name - default is "ESS Chat"
4. Tap **"Add"** in the top-right corner

### Step 3: Launch the App

1. Go to your iPhone's Home Screen
2. Find the **ESS Chat** icon (blue/cyan gradient with hexagon logo)
3. Tap to launch

## Features

Once installed, ESS Chat works like a native app:

- **Full-screen experience** - No Safari browser bars
- **Offline access** - Previously loaded pages work offline
- **Push-like notifications** - (Requires user action in the app)
- **Fast loading** - Cached resources load instantly
- **Home Screen icon** - Launch directly from your phone

## Using ESS Chat

### Ask Questions

1. Type your question in the input field
2. Tap **Send** or press Enter
3. Wait for the AI-powered response

### Handle Clarifications

If ESS needs more context:
1. You'll see clarifying questions
2. Select the relevant options
3. Get a more accurate answer

### View Evidence

- Tap on citations to see source files
- Expand code blocks to view implementation details
- Use the confidence indicator to gauge answer reliability

## Troubleshooting

### App Won't Install

- Make sure you're using Safari (not Chrome or Firefox)
- Ensure you have enough storage space
- Try clearing Safari cache: Settings → Safari → Clear History and Website Data

### App Shows Blank Screen

- Check your internet connection
- Close and reopen the app
- Remove and reinstall from Safari

### API Key Required

If you see "Unauthorized" errors:
1. Contact your administrator for an API key
2. The key will be configured in your app settings

### Slow or No Response

- Check your internet connection
- The AI synthesis can take up to 60 seconds for complex queries
- Try simplifying your question

## Removing the App

1. Press and hold the ESS Chat icon
2. Tap **"Remove App"** or the **X** button
3. Confirm removal

## Support

For issues or feedback:
- GitHub: https://github.com/anthropics/claude-code/issues
- Check the app's health status: https://ess.ping-gadgets.com/health

---

## Technical Details

ESS Chat is a Progressive Web App (PWA) with:
- Service Worker for offline caching
- Web App Manifest for native-like installation
- Responsive design optimized for mobile
- Secure HTTPS connection with TLS 1.3

**Minimum iOS Version**: 11.3 (Safari 11.1+)
**Recommended iOS Version**: 14.0 or later

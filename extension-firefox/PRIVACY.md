# PathForge Firefox extension data handling

## What the extension sends

After you choose **Connect account**, PathForge reads the existing PathForge website sign-in access token and verifies it with the PathForge API. It sends that token only to the configured PathForge backend to authenticate requests. Account identifiers accompany analysis/recommendation requests, and the backend verifies ownership.

While the connected sidebar is open, it reads the active LeetCode problem identifier, Python/Python3 source code and related editor/submission details. Opening the panel, navigating to a problem or explicitly rechecking can send that problem identifier and code to the existing PathForge backend for analysis and progress tracking. LeetCode submission details are compared locally to the captured code before displaying correctness. The extension does not execute or submit your code on LeetCode.

Requests go to `https://pathforge-v2.onrender.com`. Sign-in and detailed progress use `https://path-forge-v2.vercel.app`. Problem preparation and analysis use the existing PathForge services and their configured providers. Website/backend retention, provider processing and account-deletion practices must be described by the application's published privacy policy; this document does not claim those services store nothing.

Version 0.4.1 also sends the identifier and accepted/failed verdict of a completed
LeetCode submission when its code matches the captured solution. PathForge uses
this metadata to avoid
recording or scoring the same submission repeatedly. While the sidebar is open,
it periodically checks the displayed solution for a newly completed submission.

## What stays in the browser

The connection preference is stored locally. The access token, verified account ID/email, source-tab identifier, code fingerprint and compact analysis/recommendation cache are held in browser-session storage. The extension does not persist refresh tokens or raw code drafts. Closing the browser clears session storage. Disconnecting removes its session and result cache.

LeetCode requests use the site's existing same-origin session. The extension does not extract or forward LeetCode cookies, passwords or authentication tokens to PathForge. It does not collect general browsing history or install analytics/advertising code.

## Permissions

`storage` holds the connection preference and temporary session state. `scripting` reads the complete LeetCode editor and the existing PathForge sign-in session. Site access is limited to LeetCode and the configured PathForge website/API origins. Mozilla data categories declare authentication information, identifying account information, browsing activity (the problem identifier) and website content (the solution code).

You can disconnect through the sidebar account settings, revoke site access in the browser's extension settings, or uninstall the extension. Disconnecting/uninstalling does not delete analyses already saved to the PathForge backend; use the application's account/support controls for requests concerning those records.

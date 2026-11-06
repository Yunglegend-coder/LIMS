# Poultry Diagnostic LIMS

## Accounts and roles

Run migrations, then create or use a Django superuser to manage accounts:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

Sign in at `/accounts/login/`. The Django admin at `/admin/` lets managers assign each account a LIMS role and add the user's WhatsApp number under the profile:

- **Vet doctor:** view and send final reports.
- **Laboratory scientist:** enter and edit assay results.
- **Receptionist:** register samples, manage customer records, and send batch customer emails.
- **Manager:** access all LIMS functions.

New accounts default to Receptionist. Existing staff and superuser accounts are initialized as Manager; other existing accounts are initialized as Receptionist. Change those assignments in the admin as needed. Superusers retain full access.

## Gmail email configuration

Without SMTP credentials, email stays in development console mode and is printed in the server console. For Gmail, enable 2-Step Verification on the Google account, create an App Password, then set these Windows environment variables. Use the Gmail address that will send the messages; the App Password is not the account's normal password.

```powershell
$env:EMAIL_HOST_USER = "your.address@gmail.com"
$env:EMAIL_HOST_PASSWORD = "your-16-character-app-password"
$env:SITE_BASE_URL = "http://127.0.0.1:8000"
python manage.py runserver
```

The app selects Gmail SMTP (`smtp.gmail.com:587`, TLS) when `EMAIL_HOST_USER` is set. Set `DEFAULT_FROM_EMAIL` to the same Gmail address if you want a display name. These variables need to be present in the terminal that starts Django; for persistent use, add them through Windows Environment Variables and restart the server. Keep the App Password private and out of source control. See [Google's App Password instructions](https://support.google.com/accounts/answer/185833).

## WhatsApp Cloud API setup

WhatsApp requires a Meta developer account and a WhatsApp Business Platform Cloud API setup. Follow Meta's [Cloud API getting started guide](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started), add the WhatsApp product to a Meta app, connect/register a sender number, and obtain its Phone Number ID and an access token. Create and get approval for a message template in WhatsApp Manager. This app sends template messages with one body text parameter, so make sure the approved template has exactly one body placeholder (for example `{{1}}`).

Set the following variables in the same terminal that runs Django. Keep the access token private:

```text
WHATSAPP_ACCESS_TOKEN=your-access-token
WHATSAPP_PHONE_NUMBER_ID=your-business-phone-number-id
WHATSAPP_API_VERSION=v26.0
WHATSAPP_TEMPLATE_NAME=sample_result_notification
WHATSAPP_TEMPLATE_LANGUAGE=en_US
```

Add recipient numbers to each Vet Doctor and Laboratory Scientist profile in international format (for example `+234...`). The sending number, token, and approved template must belong to the connected Meta business account. New sample alerts create in-app notifications, send email when SMTP is configured, and send WhatsApp when the provider and template are configured. Report delivery is user-triggered from the final report page. Batch emails are individually addressed to each selected customer. See Meta's [message template documentation](https://developers.facebook.com/docs/whatsapp/business-management-api/message-templates/).

## Department dashboard

The dashboard reports monthly sample intake, open assays, and completed assays for Microbiology, Serology, and PCR / Molecular based on the assigned assay department.

## Staff chat

Use **Staff chat** in the sidebar to message any active LIMS user or post an announcement visible to all signed-in users. Direct conversation history is limited to its two participants. Open a direct conversation on both users' devices to receive and make voice calls. Calls need microphone permission and work on localhost or an HTTPS site. The app uses browser WebRTC and a public STUN server; some networks may require a TURN relay server for reliable calls, especially when users are behind restrictive firewalls or symmetric NAT. Calls are audio only and are not recorded.

## Temporary access from the same Wi-Fi network

For local testing only, start Django bound to the network interface:

```powershell
python manage.py runserver 0.0.0.0:8000
```

On the current Wi-Fi network, this computer's address is `192.168.0.189`. Other devices on the same router can open `http://192.168.0.189:8000/`. If Windows Firewall blocks it, run PowerShell as Administrator and add a rule limited to your private local subnet:

```powershell
New-NetFirewallRule -DisplayName "Poultry LIMS LAN test TCP 8000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -RemoteAddress LocalSubnet -Profile Private
```

If the router assigns this computer a different address later, update `ALLOWED_HOSTS` or set it in the environment, and use the new address. This Django development server is for trusted LAN testing only; it is not a production deployment. Browsers require HTTPS for microphone access on other devices, so voice calls over the LAN need a local HTTPS setup even when text chat works over HTTP.

## Report signatures and assay visibility

Each user can upload or replace their PNG/JPG report signature from **My signature** in the top bar. PDF and DOCX exports include the lab logo, the exporting user's signature when uploaded, and the name of the user who entered each assay. Assay types can be marked **Biochemical** in the assay admin; those results are omitted from customer exports. Sample registration pre-fills the next case code and permits a unique manually assigned code.

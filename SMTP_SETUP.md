# SMTP provider setup

For this private, one-recipient digest, start with Gmail if you already have a mailbox. Choose Brevo if you want a separate transactional sender for the automation.

## Gmail or Google Workspace

1. Turn on 2-Step Verification for the sending Google account.
2. Create a Google [App Password](https://support.google.com/mail/answer/185833). Use the generated 16-character value as `SMTP_PASSWORD`; do not use the normal Google password.
3. Configure:

   ```dotenv
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USE_TLS=true
   SMTP_USERNAME=you@gmail.com
   SMTP_PASSWORD=your_google_app_password
   EMAIL_FROM=you@gmail.com
   EMAIL_TO=your.destination@example.com
   ```

4. Use a verified send-as address for `EMAIL_FROM` if it differs from the authenticated account.

Google documents port 587 for TLS/STARTTLS and port 465 for SSL. App Passwords require 2-Step Verification and may be unavailable for some organization-managed accounts.

## Brevo SMTP relay

1. Create a Brevo account.
2. Authenticate the sending domain or verify the sender address.
3. Open SMTP/API settings, retrieve or generate an SMTP key, and copy the exact SMTP login shown there.
4. Configure:

   ```dotenv
   SMTP_HOST=smtp-relay.brevo.com
   SMTP_PORT=587
   SMTP_USE_TLS=true
   SMTP_USERNAME=your_brevo_smtp_login
   SMTP_PASSWORD=your_brevo_smtp_key
   EMAIL_FROM=verified-sender@your-domain.example
   EMAIL_TO=your.destination@example.com
   ```

5. Use the SMTP key, not a Brevo API key, as the password.

Brevo documents port 587 (or 2525) for STARTTLS and port 465 for SSL/TLS. See the [Brevo SMTP relay documentation](https://developers.brevo.com/docs/smtp-integration).

## Recommendation

Use Gmail for the first version if the message is only for you. Use Brevo if you want the digest isolated from your personal mailbox or expect to add recipients later.

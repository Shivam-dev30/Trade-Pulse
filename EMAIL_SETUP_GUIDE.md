# Email Setup Guide

Since you requested Email notifications (which is much more reliable and free compared to unofficial WhatsApp methods), here is how to set it up.

## 1. Edit your `.env` file

Open your `.env` file and add/update the following fields. 

**Note for Gmail Users**: You CANNOT use your regular password. You must generate an "App Password".

```ini
EMAIL_SENDER=your_full_email@gmail.com
EMAIL_PASSWORD=your_app_password_here
EMAIL_RECEIVER=where_you_want_alerts@example.com
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
```

## 2. How to get a Gmail App Password

1.  Go to your [Google Account Settings](https://myaccount.google.com/).
2.  Click on **Security** on the left.
3.  Under "How you sign in to Google", ensure **2-Step Verification** is turned **ON**.
4.  Once 2FA is on, search for **"App passwords"** in the top search bar (or look under 2-Step Verification > App passwords at the bottom).
5.  Create a new app password:
    *   **App name**: Enter "SupertrendBot".
    *   Click **Create**.
6.  It will give you a 16-character password (e.g., `abcd efgh ijkl mnop`).
7.  Copy this password (without spaces is fine, or with spaces) into your `.env` file as `EMAIL_PASSWORD`.

## 3. WhatsApp Option?

If you absolutely must have WhatsApp:
*   **Twilio**: You need to sign up for Twilio, get a free number, and set up a Sandbox. This expires every few days.
*   **Web Automation**: Unreliable.

**Recommendation**: Stick to Email for critical trading alerts.

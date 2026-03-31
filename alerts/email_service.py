import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER, EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT
from logger.logger import logger

def send_alert(subject: str, body: str):
    """
    Sends an email alert.
    """
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECEIVER:
        logger.warning("Email credentials missing. Alert not sent.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        # Connect to server
        server = smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT)
        server.starttls() # Secure the connection
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email alert sent to {EMAIL_RECEIVER}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")
        return False

def format_generic_alert(symbol, direction, close_price, timestamp, algo_name):
    """
    Formats the alert message for dynamically defined technical indicators.
    """
    subject = f"🔔 {algo_name} Alert: {symbol} ({direction})"
    
    currency = "₹"
    if symbol.endswith("USD") or symbol.endswith("USDT"):
        currency = "$"
        
    formatted_price = f"{close_price:.5f}".rstrip('0').rstrip('.') if close_price < 10 else f"{close_price:,.2f}"
        
    body = (
        f"{algo_name} Signal Detected (15m)\n\n"
        f"Instrument: {symbol}\n"
        f"Direction: {direction}\n"
        f"Candle Close: {currency}{formatted_price}\n"
        f"Time (IST): {timestamp}\n\n"
        f"Automated Notification by TradePulse Dashboard"
    )
    return subject, body

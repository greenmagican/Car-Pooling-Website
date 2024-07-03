from email.message import EmailMessage
import ssl
import smtplib

# Kaan Tandogan
def send_email(name, surname, from_place, to_place, phone_number,e_mail_receiver,case): # Reference: https://www.youtube.com/watch?v=ueqZ7RL8zxM&t=129s
    email_sender = '<your_email>' # Email that I'll use to send the email.
    app_password = '<your_app_password>' # Please notice that this is the password of my application and not my gmail. 
                                      # I might delete this after the demo. So, you might need to create a application from your mail.
    email_receiver = e_mail_receiver
    subject = 'About your trip'
    if case == 1:
        message_body = f'The user \"{name} {surname}\" has booked a trip of yours [which is from: \"{from_place}\", to: \"{to_place}\"]. To talk about trip details you are expected to contact him/her from the following phone number: \"{phone_number}\".'
    elif case ==2:
        message_body = f'The user \"{name} {surname}\" has cancelled a trip of yours [which is from: \"{from_place}\", to: \"{to_place}\"].".'
    elif case == 3:
        message_body = f'The driver \"{name} {surname}\" has cancelled a trip that you reserved [which was from: \"{from_place}\", to: \"{to_place}\"].".'
    msg = EmailMessage()
    msg['From'] = email_sender
    msg['To'] = email_receiver
    msg['Subject'] = subject
    msg.set_content(message_body)
    print("Driver cancelled")
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp: # Got the ssl connection, connected and sent the mail.
            smtp.login(email_sender, app_password) 
            smtp.sendmail(email_sender, email_receiver, msg.as_string())
    except Exception as e:
        print(e)

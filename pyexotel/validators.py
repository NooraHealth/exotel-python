import re

from .exceptions import ValidationError


def validate_url(value: str) -> str:
    """
        Validates whether a string is a valid url or not

        Args:
            value (str): url

        Raises:
            ValidationError: raised when an invalid url is passed
    """
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        # domain...
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    match = re.match(regex, value)

    if match is not None:
        return value
    else:
        raise ValidationError("{val} is not a valid url".format(val=value))


def validate_phone_number(value: str) -> str:
    """
        Validates the phone number based on E.164 format

        https://www.twilio.com/docs/glossary/what-e164

        Returns validated value

        Args:
            value (str): phone number

        Raises:
            ValidationError: raised when the number isn't valid
    """
    regex = re.compile(r'^\+[1-9]\d{10,14}$')
    match = re.match(regex, value)

    if match is not None:
        return value
    else:
        raise ValidationError(
            """{val} is not a valid phone number as per E.164 format
            For reference: https://www.twilio.com/docs/glossary/what-e164""".format(val=value))

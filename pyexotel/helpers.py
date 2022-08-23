from .exceptions import ValidationError
from .validators import validate_phone_number


def validate_list_of_nums(numbers):
    invalid = []
    for num in numbers:
        try:
            validate_phone_number(num)
        except ValidationError:
            invalid.append(num)

    if len(invalid) > 0:
        raise ValidationError(
            "Received invalid numbers as per E.164 format, please check")

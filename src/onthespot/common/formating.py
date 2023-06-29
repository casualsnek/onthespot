import os


def sanitize_string(
        string: str,
        skip_path_seps: bool = False,
        escape_quotes: bool = False
        ) -> str:
    """
    Sanitises path and other string to make them filename compliant
    :param string: Input string
    :param skip_path_seps:  If set to true skips removal of path separators in sting
    :param escape_quotes: Escape quotes on strings
    :return:
    """
    if string is None:
        return ''
    sanitize = ['*', '?', '<', '>', '"'] if os.name == 'nt' else []
    if os.name == 'nt':
        string = string.replace('/', '\\')
    if not skip_path_seps:
        sanitize.append(os.path.sep)
    for i in sanitize:
        string = string.replace(i, '')
    if os.name == 'nt':
        string = string.replace('|', '-')
        drive_letter, tail = os.path.splitdrive(string)
        string = os.path.join(
            drive_letter,
            tail.replace(':', '-')
        )
        string = string.rstrip('.')
    else:
        if escape_quotes and '"' in string:
            # Since convert uses double quotes, we may need to escape if it
            # exists in a path, on windows double quotes are
            # not allowed in a path and will be removed
            string = string.replace('"', '\\"')
    return string


def metadata_list_to_string(items: list[str], separator: str = ";") -> str:
    """
    Separates a list of metadata by a separator token and returns a string
    :param items: List of str containing Metadata items
    :param separator: Separator to use
    :return:
    """
    formatted: str = ""
    for item in items:
        formatted += item + separator + " "
    return formatted[:-2].strip()
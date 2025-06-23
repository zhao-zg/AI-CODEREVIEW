import re


class GitDiffParser:
    def __init__(self, diff_string):
        self.diff_string = diff_string
        self.old_code = None
        self.new_code = None

    def parse_diff(self):
        old_code = []
        new_code = []

        diff_lines = self.diff_string.splitlines()
        parsing_old_code = False
        parsing_new_code = False

        for line in diff_lines:
            # Identify the diff sections
            if line.startswith('@@'):
                parsing_old_code = False
                parsing_new_code = False
            elif line.startswith('-'):
                old_code.append(line[1:])  # Remove the leading '-' which indicates removal
                parsing_old_code = True
            elif line.startswith('+'):
                new_code.append(line[1:])  # Remove the leading '+' which indicates addition
                parsing_new_code = True
            else:
                if parsing_old_code:
                    old_code.append(line)
                if parsing_new_code:
                    new_code.append(line)

        self.old_code = '\n'.join(old_code)
        self.new_code = '\n'.join(new_code)

    def get_old_code(self):
        if self.old_code is None:
            self.parse_diff()
        return self.old_code

    def get_new_code(self):
        if self.new_code is None:
            self.parse_diff()
        return self.new_code

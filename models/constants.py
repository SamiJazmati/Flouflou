class BColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class JSFrameworks:
    ANGULAR = 'angular'
    REACT = 'react'
    VUE = 'vue'

    ALL = [ANGULAR, REACT, VUE]


class PythonFrameworks:
    DJANGO = 'django'
    FAST_API = 'fast_api'
    FLASK = 'flask'

    ALL = [DJANGO, FAST_API, FLASK]


class FastAPI:
    def __init__(self):
        self.REPO = 'Fincher'
        self.SERVICE = 'fincher'
        self.FILES_AND_REPOS = [
            f'app/{self.SERVICE}',
            f'app/tests/{self.SERVICE}_test_case.py',
        ]
        self.TEMPLATE_FILES = [
            'buildspec.yaml',
            'docker-compose.yaml',
            'Dockerrun.aws.json',
            'app/tests/__init__.py',
            f'app/tests/{self.SERVICE}_test_case.py',
            'app/tests/test_internal/test_skeleton.py',
        ]


class React:
    def __init__(self):
        self.REPO = 'Argento'
        self.SERVICE = 'argento'
        self.FILES_AND_REPOS = []
        self.TEMPLATE_FILES = ['docker-compose.yaml']

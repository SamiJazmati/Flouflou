from github import Github, GithubException


class GithubClient:
    def __init__(self, token):
        self.token = token
        self.client = Github(login_or_token=self.token)

    def _get_organisation(self, organisationName):
        try:
            return self.client.get_organization(login=organisationName)
        except GithubException as exception:
            raise SystemExit(
                f'Error: failed to get organisation {organisationName}, error response from Github: '
                f'{", ".join(self._exception_messages(exception=exception))}'
            )

    def get_repo(self, owner, repoName):
        try:
            return self.client.get_repo(full_name_or_id=f'{owner}/{repoName}')
        except GithubException as exception:
            raise SystemExit(
                f'Error: failed to get repo {repoName}, error response from Github: '
                f'{", ".join(self._exception_messages(exception=exception))}'
            )

    def create_repo(
        self,
        repoName,
        organisationName,
        gitignoreTemplate,
        autoInit,
        description,
        private,
        deleteBranchOnMerge,
    ):
        organisation = self._get_organisation(organisationName=organisationName)
        try:
            return organisation.create_repo(
                name=repoName,
                gitignore_template=gitignoreTemplate,
                auto_init=autoInit,
                description=description,
                private=private,
                delete_branch_on_merge=deleteBranchOnMerge,
            )
        except GithubException as exception:
            raise SystemExit(
                f'Error: failed to create service {repoName}, error response from Github: '
                f'{", ".join(self._exception_messages(exception=exception))}'
            )

    def create_ssh_key_for_repo(self, repo, title, key, readOnly=False):
        try:
            return repo.create_key(title=title, key=key, read_only=readOnly)
        except GithubException as exception:
            raise SystemExit(
                f'Error: failed to create ssh key for repo {repo}, error response from Github: '
                f'{", ".join(self._exception_messages(exception=exception))}'
            )

    def edit_default_branch_for_repo(self, repo, defaultBranch):
        try:
            return repo.edit(default_branch=defaultBranch)
        except GithubException as exception:
            raise SystemExit(
                f'Error: failed to set default branch {defaultBranch} for repo {repo}, error response from Github: '
                f'{", ".join(self._exception_messages(exception=exception))}'
            )

    def edit_branch_protection_rules(
        self, repo, branchName, strict, contexts, enforceAdmins
    ):
        try:
            branch = repo.get_branch(branch=branchName)
        except GithubException as exception:
            raise SystemExit(
                f'Error: failed to get branch {branchName} from repo {repo}, error response from Github: '
                f'{", ".join(self._exception_messages(exception=exception))}'
            )
        try:
            return branch.edit_protection(
                strict=strict, contexts=contexts, enforce_admins=enforceAdmins
            )
        except GithubException as exception:
            raise SystemExit(
                f'Error: failed to edit protection for {branchName}, error response from Github: '
                f'{", ".join(self._exception_messages(exception=exception))}'
            )

    @staticmethod
    def _exception_messages(exception):
        messages = []
        if exception.data:
            if exception.data.get('message'):
                messages.append(exception.data['message'])
            if exception.data.get('errors'):
                errors = exception.data['errors']
                messages.extend(
                    [error['message'] for error in errors if error.get('message')]
                )
        else:
            messages.append(exception)
        return messages

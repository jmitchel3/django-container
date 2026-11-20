# Publishing changes

After completing and verifying a requested project change, commit the relevant
files with a subject that describes the change. Push the branch to `origin`
and verify the remote received the commit. The local Git hooks normally perform
the push. Keep unrelated work out of the commit.

Use `feat:` for features and `fix:` for fixes. Mark breaking changes with
`!` before the colon or a `BREAKING CHANGE:` footer. On `main`, GitHub Actions
publishes versions and updates the changelog after the checks pass.

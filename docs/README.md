# SQLCraft GitHub Pages demo

This folder hosts a static question-bank demo. It has English/Hinglish questions,
search, difficulty filters, hints and reference solutions. It does not provide
accounts, online progress, an editor or SQL execution. The Django application
in the repository remains the full application.

## Enable free hosting

1. In this repository's **Settings → General → Danger Zone**, change visibility
   to **Public** (the owner has authorized this). Free GitHub Pages requires a
   public repository; eligible paid accounts can also host private source repos.
2. In **Settings → Pages → Build and deployment**, choose **Deploy from a branch**,
   select **development** and **/docs**, then click **Save**.

GitHub publishes the demo at https://akashVyntics.github.io/sqlcraft/ after its
Pages deployment finishes. The URL is an expected address, not evidence that
hosting has been enabled. `main` is not used or changed for this deployment.

## Update the demo

From the repository root, run `python -m scripts.build_pages` after changing the
question bank or demo builder, then commit the generated `docs/index.html` to
`development`. The Pages demo checks verify that committed output matches the
builder and that the JavaScript parses.

## If the site is not live

Confirm that Pages uses **Deploy from a branch → development → /docs**.
The `main` branch has no demo folder. The Pages demo checks workflow validates
files but does not publish them; selecting **GitHub Actions** as the Pages source
will require a separate deployment workflow. With branch publishing selected,
look for GitHub's **pages build and deployment** run in the Actions tab and
check its build and deploy jobs. Use the repository URL ending in `/sqlcraft/`,
not the account root URL.

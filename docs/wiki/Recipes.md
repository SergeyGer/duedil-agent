# Recipes

Task-first answers: find the thing you want to do, copy the command. Everything below works from
the repository root; Windows equivalents are in the second column where they differ.

*Last reviewed: 2026-10-23 · Owner: [@SergeyGer](https://github.com/SergeyGer)*

## Run the project

| I want to… | Linux / macOS | Windows |
|---|---|---|
| Start the app and open it | `./start.sh` → <http://localhost:8501> | `.\start.cmd` |
| Stop it and free the port | `./stop.sh` | `.\stop.cmd` |
| See what is running | `./scripts/project.sh status` | `.\scripts\project.ps1 status` |
| Watch the log | `./scripts/project.sh logs` | `.\scripts\project.ps1 logs` |
| Get a shell in the container | `./scripts/project.sh shell` | `.\scripts\project.ps1 shell` |
| Run one deck through the CLI | `./scripts/project.sh cli examples/cursor_deck.pdf https://cursor.com` | `.\scripts\project.ps1 cli examples\cursor_deck.pdf https://cursor.com` |
| Rebuild after changing dependencies | `./scripts/project.sh rebuild` | `.\scripts\project.ps1 rebuild` |
| Give this checkout its own port (shared server) | `./scripts/project.sh instance auto` | `.\scripts\project.ps1 instance auto` |

## Work on the code

| I want to… | Command |
|---|---|
| Run the test suite | `make test` |
| Run tests with coverage | `make coverage` |
| Format and lint | `make fmt` then `make lint` |
| Run the pre-commit hooks | `pre-commit run --all-files` |
| Run the app without Docker | `make run` |
| Run the offline demo (no API keys) | `make demo` |
| Regenerate the example decks | `python scripts/make_example_decks.py` |

## Documentation

| I want to… | Command |
|---|---|
| Validate links, anchors, ADRs and wording | `python scripts/validate_docs.py --verbose` |
| Regenerate the generated reference page | `make wiki-reference` |
| Publish the wiki | `./scripts/publish_wiki.sh` |
| Regenerate the personal Run & Stop guide | `make devcontainer-doc` (Russian), `make devcontainer-doc-en` |
| Re-record the screenshots and the demo video | `python scripts/make_demo_video.py --base-url http://127.0.0.1:8511`, then `python scripts/build_demo_video.py --capture /tmp/duedil-capture --ffmpeg $(python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")` |

## Operate and debug

| I want to… | Where |
|---|---|
| Understand a `403` from LangSmith | [Troubleshooting](Troubleshooting) |
| Know why an example still says `[NOT_FOUND]` | [Red-Flag Engine](Red-Flag-Engine) |
| Change the model or the parser | [Configuration](Configuration) |
| Understand the container and dev-container setup | [Installation & Deployment](Installation-and-Deployment) |
| Add or change a Red-Flag rule | [Extending the System](Extending-the-System) |
| Review the security posture | [Security & Limits](Security-and-Limits) |

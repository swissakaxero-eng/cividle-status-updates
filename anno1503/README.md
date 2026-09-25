# Anno 1503 Auto Trainer update channel

ANNO1503_AUTOUPDATE_CHANNEL

This folder is intentionally isolated from CivIdle despite living in the same public update repository.

- Stable manifest: `anno1503/channel.json`
- Future patch payloads: `anno1503/patches/<version>.py`
- The installed trainer keeps its editable source tree under `%LOCALAPPDATA%\Anno1503Trainer\source`.
- Updates are downloaded, SHA-256 checked, applied to that source tree, rebuilt locally, backed up, and then the stable EXE is replaced.
- No ChatGPT, Microsoft, or GitHub password/token is stored inside the trainer.

Initial bootstrap baseline: 0.10.0.

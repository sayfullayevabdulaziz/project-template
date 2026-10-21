# <project name> mobile

<!-- project-context:start -->
_Not generated yet. Fill PROJECT.md, then run /sync-context from the workspace root._
<!-- project-context:end -->

## Stack

Flutter (version pinned in `pubspec.yaml`), Riverpod 3 without codegen, go_router, dio with an auth interceptor, `swagger_parser` + retrofit + json_serializable via build_runner, flutter_secure_storage, flutter_lints with strict analysis.

## Commands

- `make bootstrap`: fetch packages and generate code; run once after cloning.
- `make dev`: run the app with `config/dev.json`.
- `make test`: run `flutter test`.
- `make lint`: run `flutter analyze`.
- `make fmt`: run `dart format`.
- `make check`: lint and tests.
- `make gen-api`: regenerate the API client from `openapi.json`.

## Architecture map

- `lib/main.dart`: entry point and provider scope.
- `lib/core/`: router, dio setup, auth interceptor, secure storage, config.
- `lib/api/`: generated API client. Never edit.
- `lib/features/<name>/`: screens, providers and widgets per domain feature.
- `config/`: `--dart-define-from-file` JSON per environment.
- `openapi.json`: copy of the backend `public` spec, written by `make sync-api` at the workspace root.

## Conventions

- Call the API only through the generated client.
- State lives in Riverpod providers; widgets stay thin.
- Use the glossary words from PROJECT.md in code and UI.
- Installed apps live for months: tolerate unknown fields and handle every error state.
- Tokens go in secure storage, never in preferences.

## Testing

- Unit tests for providers and repositories; widget tests for screens.
- Fake the API client; do not hit the network.
- Add a test with every screen or provider you add.

## Definition of done

- `make check` is green.
- The client is regenerated after any spec change (`make gen-api`).
- The UI works for loading, empty and error states.

## Never

- Edit generated code.
- Hand-edit `openapi.json`; change the backend and run `make sync-api`.
- Commit secrets or real `config/*.json` values.
- Put business rules in widgets; the backend enforces them.
- Call `/api/admin` from this app; it uses `/api/v1` only.

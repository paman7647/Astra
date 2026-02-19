# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.2b5] - 2026-02-20

### Added
- **Force Fetching Support**: Added `force` parameter to `Client.fetch_messages` and bridge-level `fetchMessages` to bypass internal caches and retrieve fresh data directly from WhatsApp storage.
- **High-Level Media Methods**: Added `send_image`, `send_video`, `send_audio`, and `send_sticker` directly to `Client`.
- **Client.delete_message Shortcut**: Introduced a streamlined `delete_message` method in the `Client` class for easier moderation plugin development.
- **Centralized Plugin Imports**: Command modules can now use `from . import *` to access core framework and utility symbols from the package level.
- **Smart Sticker Handling**: `send_sticker` now supports both file paths and Base64 data strings.
- **Client Shortcuts**: Exposed media methods (`send_audio`, `download_media`, etc.) as first-class citizens on the `Client` instance.

### Fixed
- **Mention Parsing Resilience**: Fixed `TypeError` in `Message.from_payload` by ensuring `mentionedJidList` gracefully handles `null` or missing values.
- **Plugin Compatibility**: Restored `download_media` and patched `send_media` to support `reply_to`, fixing crashes in plugins like `sticker`, `spotify`, and `youtube`.
- **Bridge Argument Normalization**: Updated `Astra.fetchMessages` (JS) to robustly handle both positional and dictionary-based argument payloads.
- **Userbot Response Loops**: Refined `purge` and `smart_reply` logic to prevent message editing failures when the status message and command message are the same.
- **Stability**: Standardized codebase with professional headers and updated repository branding (`Astra-Userbot`).

## [0.0.1b4] - 2026-02-19

### Added
- **Rate-limit protection for edits**: Integrated a mandatory 0.5s stability delay in `Message.edit` and `ChatMethods.edit_message`. This helps prevent WhatsApp rate limits and race conditions when performing rapid-fire edits.

### Fixed
- **Attribute cleanup**: Standardized on `is_media` globally to eliminate sporadic `AttributeError` crashes related to legacy `has_media` property.
- **Quoted media extraction**: Refined the model to accurately detect quoted stickers and media even when received as skeletal payloads.

### Changed
- **Unthrottled deletions**: Intentionally kept deletion methods fast. Multi-message removal remains high-speed without artificial delays.
- **Documentation**: Updated the Sphinx guide to reflect framework-level timing management, reducing the need for manual sleeps in custom handlers.

## [0.0.1b3] - 2026-02-17

### Added
- **Phone Pairing Support**: Added native support for linking via phone number in terminal-based environments.
- **Rate Limit Handling**: Enhanced detection of "Too many attempts" during phone pairing to prevent silent failures.
- **Reliability**: Optimized browser state detection order for pairing.

### Changed
- **Documentation**: Internal docstrings and comments refined for improved technical clarity.
- **Dependency**: Updated version to `0.0.1b3`.


## [0.0.1b1] - 2026-02-16

### Added
- **Core Engine**: Asynchronous, Playwright-based WhatsApp Web automation.
- **Multi-Device Support**: Full support for MD beta and stable versions.
- **Messaging**: Text, replies, mentions, editing, and deletion supported.
- **Media Support**: Send/Receive images, videos, audio, documents, and stickers.
- **Interaction**: reaction to messages, poll creation, and event handling.
- **Group Management**: Admin tools for promoting, demoting, and managing participants.
- **Privacy Controls**: Settings for profile picture, status, and last seen visibility.
- **Documentation**: Comprehensive README, Sphinx docs, and 6 examples.
- **Infrastructure**: GitHub Actions CI, Dependabot, and Issue Templates.

### Changed
- **Dependencies**: Made `qrcode`, `Pillow`, and `requests` mandatory core dependencies.
- **Repository**: Clean rewrite of the codebase for public beta release.

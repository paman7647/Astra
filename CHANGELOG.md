# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

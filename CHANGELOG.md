# Changelog

All notable changes to the Charli3 Push Oracle Node will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v3.5.7] - 2026-01-15

### 🎉 First Release

### Added
- **LP Token Adapter**: Support for DEX liquidity token pricing
  - Enables pricing of LP tokens from Cardano DEXes
  - Automatic pool selection based on liquidity and data freshness
  - Support for multiple DEX protocols
  - Comprehensive asset naming and validation
  - Full test coverage for LP token pricing logic

- **Repository Standards**: Complete open-source project structure
  - Issue and PR templates for better collaboration
  - Contributing guidelines (CONTRIBUTING.md)
  - Security policy (SECURITY.md)
  - Code of conduct (CODE_OF_CONDUCT.md)

### Changed
- **SDK Integration**: Now using [Charli3 Push Oracle SDK](https://github.com/Charli3-Official/charli3-push-oracle-sdk) v1.8.8
  - Fully open-source and accessible to the community
  - Simplified installation process - no SSH keys required

- **Updated README**:
  - Links to SDK documentation
  - Updated tested versions: Cardano-node v10.1.4, Ogmios v6.11.0, Kupo v2.10.0
  - Improved setup instructions

### Removed
- **SSH Requirements**: Completely eliminated SSH dependencies
  - Removed SSH setup from Dockerfile
  - Removed SSH configuration from all GitHub Actions workflows
  - Simplified CI/CD pipelines

- **Cryptodome Dependency**: Removed deprecated cryptodome library

### Fixed
- Documentation improvements and corrections in adapter examples
- Security policy cleanup and formatting

## [v3.4.0] - 2025-06-09

### Added
- **HOSKY Oracle Feed Precision Fix**: Configurable precision multiplier for accurate micro-cap token pricing
  - Added `precision_multiplier` parameter to `FeedUpdater` constructor with default value of 1,000,000 (1e6)
  - Added `precision_multiplier` configuration option in Rate section of config files
  - Converted `_calculate_rate` from static method to instance method using configurable precision
  - Added comprehensive test suite in `test_precision_multiplier.py` with 9 test cases
  - Updated example configuration with precision multiplier documentation
  - Full backward compatibility maintained for existing feeds

### Changed
- `FeedUpdater._calculate_rate()` now uses instance `precision_multiplier` instead of hardcoded 1e6
- `setup_feed_updater()` in `app_setup.py` now reads and passes `precision_multiplier` from config
- Updated existing tests to include new `precision_multiplier` parameter

### Technical Details
- **Problem Solved**: HOSKY/ADA feed had 1,394% error due to insufficient precision (0.00000006691 ADA → 0.000001 ADA)
- **Solution**: Configurable precision multiplier allows 1e12 precision for HOSKY (error reduced to <0.0000001%)
- **Impact**: Perfect accuracy for micro-cap tokens while maintaining compatibility with existing feeds
- **Configuration**: Set `precision_multiplier: 1000000000000` in Rate section for HOSKY-like tokens

### Migration Guide
- Existing configurations continue to work without changes (default precision_multiplier: 1000000)
- For micro-cap tokens, add `precision_multiplier: 1000000000000` to the Rate section in config.yml
- No database migrations required - implementation is purely configuration-driven

## [v3.3.0] and earlier
- See git history for previous changes

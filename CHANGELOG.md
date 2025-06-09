# Changelog

All notable changes to the Charli3 Node Operator Backend will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

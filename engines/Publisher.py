"""
===============================================================================
Module: Publisher.py
Role: Cross-Repository Automated Publisher (Zero-Touch Showcase)
===============================================================================

Architectural Guidelines & Constraints for Implementation:

1. Cross-Repository Authentication (Security & Access):
   - The default `GITHUB_TOKEN` provided by GitHub Actions only grants access
     to the current repository (OffSec-Terminal-Forge).
   - To push updates to the profile repository (Ahmed-Roshdi/Ahmed-Roshdi),
     this script MUST be executed using a Personal Access Token (PAT) with
     full `repo` scope. This PAT must be stored as a GitHub Secret.

2. Safe Content Injection (State Preservation):
   - The target README.md in the profile repository contains static personal
     data that must not be overwritten.
   - Implementation must use HTML marker comments to define the injection zone.
     Example markers:
     <!-- OFFSEC-FORGE-START -->
     ... dynamic content goes here ...
     <!-- OFFSEC-FORGE-END -->
   - Use Regular Expressions (Regex) to locate these exact markers and replace
     only the content between them, preserving the rest of the file's integrity.

3. Absolute Asset Linking (Branch Isolation):
   - Since the automated assets are now strictly isolated in the `Output` branch,
     relative paths will result in broken images on the profile README.
   - All image URLs injected by this script MUST be absolute raw URLs pointing
     specifically to the `Output` branch.
     Format: https://raw.githubusercontent.com/Ahmed-Roshdi/OffSec-Terminal-Forge/Output/output/...

===============================================================================
"""

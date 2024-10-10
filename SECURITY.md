# Security Policy

## Supported Versions

This section outlines which versions of our project are currently being supported with security updates. Only the latest version will receive patches for any security vulnerabilities identified.

| Version | Supported          |
| ------- | ------------------ |
|  1.x.x  | :white_check_mark: |

## API Keys

To protect sensitive data, **do not** upload API keys to GitHub or include them directly in your source code. Follow these guidelines for securing API keys:
- **`.gitignore` Configuration**: Ensure that files containing API keys (e.g., `.env` files) are added to `.gitignore` to prevent them from being committed to the repository.
- **Accidental Exposure**: If you accidentally upload an API key, take these steps immediately:
  - **Remove the Key**: Delete the exposed key from your repository history using tools like `git filter-repo` or `BFG Repo-Cleaner`.
  - **Revoke and Regenerate**: Revoke the compromised key in the API provider's dashboard and generate a new one.
  - **Inform IT**: Communicate the incident with the IT team at **itsupport@medfac.co.uk**.

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it to our IT team immediately. We take all security concerns seriously and will address them as quickly as possible.

### How to Report

- **Contact**: Send an email to **itsupport@medfac.co.uk** with the details of the vulnerability.
- **Include the Following Information**:
  - A **detailed description** of the vulnerability, including steps to reproduce it.
  - The **potential impact** of the vulnerability and any suggestions for mitigating it.
  - Any **proof-of-concept** code or screenshots that can help us better understand the issue.

## Internal Use Only

- This software is intended for **internal use only**. Do not share or distribute this software outside of the company without explicit permission.
- **Do not download** or transfer this software outside of the designated **virtual machine environment** without consulting the IT team first. If you need to use the software outside of its approved environment, contact **itsupport@medfac.co.uk** for guidance.

# Halo Medical Code Automation

<p align="center">
    <img src="images/HALO(TM)_Logo.png" width="400" alt="Halo Logo">
</p>

## Overview
**Halo-AI-Coder** is an internal tool developed for the price coding department at Halo Medical. It leverages AI to price code prescription forms in guidance with the NHS recommendations. The project integrates with various APIs to streamline the price coding process.

## Tools
- **Python 3.12**
- **Azure Document Intelligence API**: Used for reading the PDF forms and converting them to text.
- **OpenAI API (gpt_4o_08_05)**: Utilised for price coding the converted text using logic text files as a prompt.

## Features
- Feature 1: Upload PDFs
- Feature 2: Drag and drop PDFs (to increase productivity)
- Feature 3: Switching themes (accessibility)

## Supported Form Types
- Insole Forms

## Prerequisites
- Python 3.12 installed on your system (does not effect users if they use the exe)
- Access to the Azure Document Intelligence API
- API key for OpenAI's gpt_4o_08_05

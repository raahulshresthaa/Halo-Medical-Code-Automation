# Halo Medical Code Automation

<p align="center">
    <img src="images/HALO(TM)_Logo.png" width="400" alt="Halo Logo">
</p>

## Overview
**Halo-AI-Coder** is an internal tool developed for the price coding department at Halo Medical. It leverages advanced AI and cloud-based services to automate the price coding of prescription forms in alignment with NHS recommendations. The project integrates with various APIs to streamline the price coding process, significantly reducing time and errors compared to manual methods.

The application now uses a **hybrid AI and manual coding approach**, where manually coded data is passed into a fine-tuned **OpenAI model**. This model applies corrections based on additional information and fine-tuned training data, enhancing accuracy and adaptability. The system is capable of processing multiple form types and providing additional functionalities.

## Tools
- **Python 3.12**: The core programming language used for the application.
- **Azure Document Intelligence API**: This API is used for reading and interpreting the PDF forms, converting the document content into structured text data.
- **OpenAI API (fine-tuned model)**: The AI model processes the extracted and manually coded data, applying logic defined through fine-tuned training to produce accurate and consistent outputs.

## Features
- **Upload PDFs**: Users can upload PDF forms directly into the application, allowing the system to read and process multiple documents seamlessly.
- **Drag and Drop PDFs**: To increase productivity, users can drag and drop PDF files directly into the interface, speeding up the workflow and reducing time spent navigating file directories.
- **Theme Switching**: Offers multiple theme options to improve accessibility, allowing users to choose between light and dark themes or other custom styles for better visibility and comfort during long sessions.
- **Automated Data Extraction**: Utilises a custom form reader from Azure Document Intelligence to automatically extract relevant information from prescription forms. This process eliminates the need for manual data entry and ensures consistency.
- **Hybrid AI-Powered Price Coding**: The system combines manual coding with AI processing to assign accurate price codes. The OpenAI model applies fine-tuned training data to make corrections and enhancements based on additional information.
- **Supports Multiple Form Types**: Now processes:
  - **Insole Forms**
  - **AFO (Ankle-Foot Orthosis) Forms**
  - **Bespoke Forms**
  - **Modular Forms**
- **Tariff Code Support**: Provides tariff codes for selected clinics to further streamline coding workflows.
- **Fast Processing Time**: The entire extraction and price coding process takes about **5 seconds**, allowing the department to handle a high volume of forms efficiently.
- **Results Logging**: Every API call, including the extracted data and the resulting price codes, is recorded in a **results log**. A new log file is generated each day, making it easier to organise and review past results, monitor accuracy, and track any discrepancies.

## Prerequisites
- **Python 3.12** installed on your system (this is not required for users who use the standalone executable version of the application).
- **Access to the Azure Document Intelligence API**: Required to enable the custom document reader functionality.
- **API key for OpenAI's fine-tuned model**: Necessary for secure communication with the OpenAI model to perform price coding.

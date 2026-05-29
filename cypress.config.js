const { defineConfig } = require("cypress");

module.exports = defineConfig({
  e2e: {
    // O backend FastAPI serve o dashboard e a API na mesma origem.
    baseUrl: "http://127.0.0.1:8000",
    specPattern: "cypress/e2e/**/*.cy.js",
    supportFile: false,
    video: false,
    screenshotsFolder: "cypress/screenshots",
    viewportWidth: 1440,
    viewportHeight: 1000,
  },
});

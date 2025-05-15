module.exports = [
  {
    files: ["**/*.js"],
    languageOptions: {
      ecmaVersion: 2021, // This must be a number, not a string
      sourceType: "module",
      globals: {
        window: true, // Example globals for browser environment
        document: true,
        console: true,
      },
    },
    rules: {
      "no-unused-vars": ["error"],        // Fail the pipeline on unused variables
      "indent": ["error", 2],             // Enforce 2 spaces for indentation
      "quotes": ["warn", "double"],       // Warn for the use of double quotes
    },
  },
];

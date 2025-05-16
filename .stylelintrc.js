module.exports = {
  extends: ["stylelint-config-standard"],
  rules: {
    "selector-class-pattern": null, // Ignore kebab-case check if needed
    "no-empty-source": null, // Disable unnecessary checks for empty files
  },
};

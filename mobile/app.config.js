// JavaScript keeps Expo/EAS config readable on Node builds without TypeScript support.
module.exports = ({ config }) => ({
  ...config,
  name: 'SYNESIS movil',
  slug: 'synesis-movil',
  plugins: [...(config.plugins || []), ['expo-build-properties', { android: { usesCleartextTraffic: process.env.EAS_BUILD_PROFILE === 'development' } }]],
  ios: { ...config.ios, bundleIdentifier: process.env.SYNESIS_IOS_BUNDLE_ID || config.ios?.bundleIdentifier },
  android: { ...config.android, package: process.env.SYNESIS_ANDROID_PACKAGE || config.android?.package,
    ...(process.env.GOOGLE_SERVICES_JSON ? { googleServicesFile: process.env.GOOGLE_SERVICES_JSON } : {}) },
  extra: { ...config.extra, ...(process.env.EXPO_PUBLIC_EAS_PROJECT_ID ? { eas: { ...config.extra?.eas, projectId: process.env.EXPO_PUBLIC_EAS_PROJECT_ID } } : {}) },
});

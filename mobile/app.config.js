// JavaScript keeps Expo/EAS config readable on Node builds without TypeScript support.
const isDevClient = process.env.EAS_BUILD_PROFILE === 'development';

module.exports = ({ config }) => ({
  ...config,
  name: isDevClient ? 'SYNESIS Dev' : 'SYNESIS movil',
  slug: 'synesis-movil',
  scheme: isDevClient ? 'synesismovil-dev' : (config.scheme || 'synesismovil'),
  plugins: [
    ...(config.plugins || []),
    [
      'expo-build-properties',
      {
        android: {
          usesCleartextTraffic:
            isDevClient || process.env.EXPO_PUBLIC_ALLOW_LOCAL_HTTP === 'true',
        },
      },
    ],
  ],
  ios: {
    ...config.ios,
    bundleIdentifier:
      process.env.SYNESIS_IOS_BUNDLE_ID ||
      (isDevClient
        ? 'net.sytes.emr.synesismovil.dev'
        : config.ios?.bundleIdentifier),
  },
  android: {
    ...config.android,
    package:
      process.env.SYNESIS_ANDROID_PACKAGE ||
      (isDevClient
        ? 'net.sytes.emr.synesismovil.dev'
        : config.android?.package),
    ...(process.env.GOOGLE_SERVICES_JSON
      ? { googleServicesFile: process.env.GOOGLE_SERVICES_JSON }
      : {}),
  },
  extra: {
    ...config.extra,
    ...(process.env.EXPO_PUBLIC_EAS_PROJECT_ID
      ? {
          eas: {
            ...config.extra?.eas,
            projectId: process.env.EXPO_PUBLIC_EAS_PROJECT_ID,
          },
        }
      : {}),
  },
});

/**
 * Centralized configuration for the application.
 */
export const config = {
    jurisdiction: {
        default: process.env.NEXT_PUBLIC_DEFAULT_JURISDICTION || 'dc',
        supported: ['dc'], // Add 'ca', 'ny', etc. here in the future
    },
    pagination: {
        defaultLimit: 50,
        maxLimit: 100,
    },
};

/**
 * Get the current jurisdiction.
 * In the future, this could read from a cookie, URL param, or user profile.
 */
export function getCurrentJurisdiction(): string {
    return config.jurisdiction.default;
}

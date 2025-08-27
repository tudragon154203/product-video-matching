import '@testing-library/jest-dom';

// Mock next/navigation
jest.mock('next/navigation', () => ({
    useRouter() {
        return {
            push: jest.fn(),
            replace: jest.fn(),
            prefetch: jest.fn(),
            back: jest.fn(),
            forward: jest.fn(),
            refresh: jest.fn(),
            pathname: '/',
            query: {},
            asPath: '/',
        };
    },
    usePathname() {
        return '/';
    },
    useSearchParams() {
        return new URLSearchParams();
    },
}));

// Mock next-intl
jest.mock('next-intl', () => ({
    useTranslations: (namespace) => (key) => {
        // If no namespace is provided, use the key directly
        if (!namespace) {
            const translations = {
                'errors.loadFailed': 'Failed to load data.',
                'errors.retry': 'Retry'
            };
            return translations[key] || key;
        }
        
        // If a namespace is provided, prepend it to the key
        const fullKey = `${namespace}.${key}`;
        const translations = {
            'jobResults.videos.panelTitle': 'Videos',
            'jobResults.products.panelTitle': 'Products',
            'jobResults.loading': 'Loading',
            'jobResults.videos.loading': 'Loading',
            'jobResults.products.loading': 'Loading',
            'jobResults.meta.video': 'video',
            'jobResults.meta.videos': 'videos'
        };
        return translations[fullKey] || fullKey;
    },
}));
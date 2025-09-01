/**
 * @jest-environment jsdom
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThumbnailImage } from '@/components/common/ThumbnailImage';

// Mock Next.js Image component
jest.mock('next/image', () => ({
    __esModule: true,
    default: function MockImage(props: any) {
        const { onError, onLoad, fill, ...otherProps } = props;
        const imgProps: any = {
            ...otherProps,
            onError,
            onLoad,
            'data-testid': 'next-image'
        };

        // Handle fill prop as boolean attribute
        if (fill) {
            imgProps.fill = '';
        }

        return React.createElement('img', imgProps);
    },
}));

describe('ThumbnailImage', () => {
    afterEach(() => {
        jest.clearAllMocks();
    });

    it('should render with correct dimensions and styling', () => {
        render(React.createElement(ThumbnailImage, { src: 'test.jpg', alt: 'Test image' }));

        const thumbnail = screen.getByTestId('thumbnail-image');
        expect(thumbnail).toHaveClass('w-[120px]', 'h-[120px]', 'rounded-md', 'bg-muted');
    });

    it('should render placeholder when src is not provided', () => {
        render(React.createElement(ThumbnailImage, { src: null, alt: '' }));

        expect(screen.getByTestId('thumbnail-placeholder-icon')).toBeInTheDocument();
        expect(screen.queryByTestId('next-image')).not.toBeInTheDocument();
    });

    it('should render placeholder when src is empty string', () => {
        render(React.createElement(ThumbnailImage, { src: '', alt: '' }));

        expect(screen.getByTestId('thumbnail-placeholder-icon')).toBeInTheDocument();
        expect(screen.queryByTestId('next-image')).not.toBeInTheDocument();
    });

    it('should render image with correct props when src is provided', () => {
        const src = 'https://example.com/image.jpg';
        const alt = 'Test product image';

        render(React.createElement(ThumbnailImage, { src, alt }));

        const image = screen.getByTestId('next-image');
        expect(image).toHaveAttribute('src', src);
        expect(image).toHaveAttribute('alt', alt);
        expect(image).toHaveAttribute('loading', 'lazy');
    });

    it('should show loading state initially when image is provided', () => {
        render(React.createElement(ThumbnailImage, { src: 'test.jpg', alt: 'Test' }));

        expect(screen.getByTestId('thumbnail-loading-icon')).toBeInTheDocument();
    });

    it('should hide loading state after image loads', async () => {
        render(React.createElement(ThumbnailImage, { src: 'test.jpg', alt: 'Test' }));

        const image = screen.getByTestId('next-image');
        fireEvent.load(image);

        await waitFor(() => {
            expect(screen.queryByTestId('thumbnail-loading-icon')).not.toBeInTheDocument();
        });
    });

    it('should show placeholder when image fails to load', async () => {
        render(React.createElement(ThumbnailImage, { src: 'invalid.jpg', alt: 'Test' }));

        const image = screen.getByTestId('next-image');
        fireEvent.error(image);

        await waitFor(() => {
            expect(screen.getByTestId('thumbnail-placeholder-icon')).toBeInTheDocument();
            expect(screen.queryByTestId('next-image')).not.toBeInTheDocument();
        });
    });

    it('should render with custom className', () => {
        const customClass = 'custom-thumbnail-class';
        render(React.createElement(ThumbnailImage, {
            src: 'test.jpg',
            alt: 'Test',
            className: customClass
        }));

        const thumbnail = screen.getByTestId('thumbnail-image');
        expect(thumbnail).toHaveClass(customClass);
    });

    it('should render with custom data-testid', () => {
        const testId = 'custom-thumbnail';
        render(React.createElement(ThumbnailImage, {
            src: 'test.jpg',
            alt: 'Test',
            'data-testid': testId
        }));

        expect(screen.getByTestId(testId)).toBeInTheDocument();
    });

    it('should use empty alt when alt is not provided or empty', () => {
        render(React.createElement(ThumbnailImage, { src: 'test.jpg', alt: '' }));

        const image = screen.getByTestId('next-image');
        expect(image).toHaveAttribute('alt', '');
    });

    it('should have proper accessibility attributes', () => {
        render(React.createElement(ThumbnailImage, {
            src: 'test.jpg',
            alt: 'Product thumbnail'
        }));

        const image = screen.getByTestId('next-image');
        expect(image).toHaveAttribute('alt', 'Product thumbnail');
    });

    it('should maintain aspect ratio with object-cover', () => {
        render(React.createElement(ThumbnailImage, { src: 'test.jpg', alt: 'Test' }));

        const image = screen.getByTestId('next-image');
        expect(image).toHaveClass('object-cover');
    });

    it('should use fill layout for responsive sizing', () => {
        render(React.createElement(ThumbnailImage, { src: 'test.jpg', alt: 'Test' }));

        const image = screen.getByTestId('next-image');
        expect(image).toHaveAttribute('fill');
    });
});
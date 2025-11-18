import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConfirmationDialog } from '../ConfirmationDialog';

describe('ConfirmationDialog', () => {
  const mockOnOpenChange = jest.fn();
  const mockOnConfirm = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should not render when open is false', () => {
    render(
      <ConfirmationDialog
        open={false}
        onOpenChange={mockOnOpenChange}
        title="Test Title"
        description="Test description"
        confirmText="Confirm"
        onConfirm={mockOnConfirm}
      />
    );

    expect(screen.queryByText('Test Title')).not.toBeInTheDocument();
  });

  it('should render when open is true', () => {
    render(
      <ConfirmationDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        title="Test Title"
        description="Test description"
        confirmText="Confirm"
        onConfirm={mockOnConfirm}
      />
    );

    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('Test description')).toBeInTheDocument();
    expect(screen.getByText('Confirm')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('should render custom cancel text', () => {
    render(
      <ConfirmationDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        title="Test Title"
        description="Test description"
        confirmText="Confirm"
        cancelText="No thanks"
        onConfirm={mockOnConfirm}
      />
    );

    expect(screen.getByText('No thanks')).toBeInTheDocument();
  });

  it('should render React node as description', () => {
    const description = (
      <div>
        <p>First paragraph</p>
        <p>Second paragraph</p>
      </div>
    );

    render(
      <ConfirmationDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        title="Test Title"
        description={description}
        confirmText="Confirm"
        onConfirm={mockOnConfirm}
      />
    );

    expect(screen.getByText('First paragraph')).toBeInTheDocument();
    expect(screen.getByText('Second paragraph')).toBeInTheDocument();
  });

  it('should call onConfirm when confirm button is clicked', () => {
    render(
      <ConfirmationDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        title="Test Title"
        description="Test description"
        confirmText="Confirm"
        onConfirm={mockOnConfirm}
      />
    );

    fireEvent.click(screen.getByText('Confirm'));

    expect(mockOnConfirm).toHaveBeenCalledTimes(1);
  });

  it('should disable buttons when isLoading is true', () => {
    render(
      <ConfirmationDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        title="Test Title"
        description="Test description"
        confirmText="Confirm"
        onConfirm={mockOnConfirm}
        isLoading={true}
      />
    );

    const confirmButton = screen.getByText('Processing...');
    const cancelButton = screen.getByText('Cancel');

    expect(confirmButton).toBeDisabled();
    expect(cancelButton).toBeDisabled();
  });

  it('should show "Processing..." text when isLoading is true', () => {
    render(
      <ConfirmationDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        title="Test Title"
        description="Test description"
        confirmText="Confirm"
        onConfirm={mockOnConfirm}
        isLoading={true}
      />
    );

    expect(screen.getByText('Processing...')).toBeInTheDocument();
    expect(screen.queryByText('Confirm')).not.toBeInTheDocument();
  });

  it('should apply destructive styling when variant is destructive', () => {
    render(
      <ConfirmationDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        title="Test Title"
        description="Test description"
        confirmText="Delete"
        onConfirm={mockOnConfirm}
        variant="destructive"
      />
    );

    const confirmButton = screen.getByText('Delete');
    expect(confirmButton).toHaveClass('bg-destructive');
  });

  it('should not apply destructive styling when variant is default', () => {
    render(
      <ConfirmationDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        title="Test Title"
        description="Test description"
        confirmText="Confirm"
        onConfirm={mockOnConfirm}
        variant="default"
      />
    );

    const confirmButton = screen.getByText('Confirm');
    expect(confirmButton).not.toHaveClass('bg-destructive');
  });

  it('should prevent default behavior on confirm button click', () => {
    render(
      <ConfirmationDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        title="Test Title"
        description="Test description"
        confirmText="Confirm"
        onConfirm={mockOnConfirm}
      />
    );

    const confirmButton = screen.getByText('Confirm');
    const event = new MouseEvent('click', { bubbles: true, cancelable: true });
    const preventDefaultSpy = jest.spyOn(event, 'preventDefault');

    fireEvent(confirmButton, event);

    expect(preventDefaultSpy).toHaveBeenCalled();
  });

  it('should not call onConfirm when buttons are disabled', () => {
    render(
      <ConfirmationDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        title="Test Title"
        description="Test description"
        confirmText="Confirm"
        onConfirm={mockOnConfirm}
        isLoading={true}
      />
    );

    const confirmButton = screen.getByText('Processing...');
    fireEvent.click(confirmButton);

    expect(mockOnConfirm).not.toHaveBeenCalled();
  });
});

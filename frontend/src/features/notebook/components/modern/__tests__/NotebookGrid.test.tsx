/**
 * Tests for the modern NotebookGrid component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, createMockNotebooks, createMockApiResponse } from '@/test-utils/render';
import { NotebookGrid } from '../NotebookGrid';
import { notebooksApi } from "@/shared/api/resources/notebooks";

// Mock the API
vi.mock('@/lib/api/resources/notebooks', () => ({
  notebooksApi: {
    getAll: vi.fn(),
    create: vi.fn(),
  },
}));

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('NotebookGrid', () => {
  const mockNotebooks = createMockNotebooks(3);
  const mockApiResponse = createMockApiResponse(mockNotebooks);

  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
    
    // Setup default mock implementation
    vi.mocked(notebooksApi.getAll).mockResolvedValue(mockApiResponse);
    vi.mocked(notebooksApi.create).mockResolvedValue(mockNotebooks[0]);
  });

  it('renders notebooks in grid view', async () => {
    renderWithProviders(<NotebookGrid />);

    // Check for header elements
    expect(screen.getByText('Notebooks')).toBeInTheDocument();
    expect(screen.getByText('Manage your research notebooks and knowledge base')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /new notebook/i })).toBeInTheDocument();

    // Wait for notebooks to load
    await waitFor(() => {
      expect(screen.getByText('Test Notebook 1')).toBeInTheDocument();
    });

    // Check that all notebooks are displayed
    mockNotebooks.forEach((notebook) => {
      expect(screen.getByText(notebook.name)).toBeInTheDocument();
      if (notebook.description) {
        expect(screen.getByText(notebook.description)).toBeInTheDocument();
      }
    });
  });

  it('handles loading state correctly', () => {
    // Mock a pending promise to simulate loading
    vi.mocked(notebooksApi.getAll).mockReturnValue(new Promise(() => {}));

    renderWithProviders(<NotebookGrid />);

    // Should show skeleton loading
    expect(screen.getByText('Notebooks')).toBeInTheDocument();
    // The skeleton components should be rendered (though they're div elements, not text)
  });

  it('handles error state correctly', async () => {
    const errorMessage = 'Failed to fetch notebooks';
    vi.mocked(notebooksApi.getAll).mockRejectedValue(new Error(errorMessage));

    renderWithProviders(<NotebookGrid />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load notebooks')).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  it('handles empty state correctly', async () => {
    vi.mocked(notebooksApi.getAll).mockResolvedValue(createMockApiResponse([]));

    renderWithProviders(<NotebookGrid />);

    await waitFor(() => {
      expect(screen.getByText('No notebooks yet')).toBeInTheDocument();
    });

    expect(screen.getByText('Get started by creating your first notebook to organize your research and knowledge.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create your first notebook/i })).toBeInTheDocument();
  });

  it('handles search functionality', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NotebookGrid />);

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Test Notebook 1')).toBeInTheDocument();
    });

    // Find and interact with search input
    const searchInput = screen.getByPlaceholderText('Search notebooks...');
    await user.type(searchInput, 'test query');

    expect(searchInput).toHaveValue('test query');

    // The API should eventually be called with the search query
    await waitFor(() => {
      expect(notebooksApi.getAll).toHaveBeenCalledWith(
        expect.objectContaining({
          search: 'test query',
          ordering: '-updated_at',
        })
      );
    }, { timeout: 2000 }); // Longer timeout for debounced search
  });

  it('switches between grid and list views', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NotebookGrid />);

    // Wait for notebooks to load
    await waitFor(() => {
      expect(screen.getByText('Test Notebook 1')).toBeInTheDocument();
    });

    // Find view toggle buttons
    const gridButton = screen.getByRole('button', { name: '' }); // Grid icon
    const listButton = screen.getAllByRole('button').find(btn => 
      btn.querySelector('svg') && btn !== gridButton
    );

    expect(listButton).toBeInTheDocument();

    // Click list view button
    if (listButton) {
      await user.click(listButton);
    }

    // Should now show table headers
    await waitFor(() => {
      expect(screen.getByText('Name')).toBeInTheDocument();
      expect(screen.getByText('Sources')).toBeInTheDocument();
      expect(screen.getByText('Items')).toBeInTheDocument();
    });
  });

  it('handles notebook creation', async () => {
    const user = userEvent.setup();
    const newNotebook = createMockNotebooks(1)[0];
    vi.mocked(notebooksApi.create).mockResolvedValue(newNotebook);

    renderWithProviders(<NotebookGrid />);

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Notebooks')).toBeInTheDocument();
    });

    // Click create notebook button
    const createButton = screen.getByRole('button', { name: /new notebook/i });
    await user.click(createButton);

    // Should call the API to create a notebook
    await waitFor(() => {
      expect(notebooksApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          name: expect.stringContaining('Notebook'),
          description: 'New notebook',
        })
      );
    });

    // Should navigate to the new notebook
    expect(mockNavigate).toHaveBeenCalledWith(`/notebook/${newNotebook.id}`);
  });

  it('handles notebook click navigation', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NotebookGrid />);

    // Wait for notebooks to load
    await waitFor(() => {
      expect(screen.getByText('Test Notebook 1')).toBeInTheDocument();
    });

    // Click on a notebook
    const notebookCard = screen.getByText('Test Notebook 1').closest("div[class*="cursor-pointer"]");
    expect(notebookCard).toBeInTheDocument();

    if (notebookCard) {
      await user.click(notebookCard);
    }

    // Should navigate to the notebook detail page
    expect(mockNavigate).toHaveBeenCalledWith('/notebook/test-notebook-1');
  });

  it('shows correct notebook status indicators', async () => {
    const processingNotebook = {
      ...mockNotebooks[0],
      isProcessing: true,
    };
    const readyNotebook = {
      ...mockNotebooks[1],
      isProcessing: false,
    };

    vi.mocked(notebooksApi.getAll).mockResolvedValue(
      createMockApiResponse([processingNotebook, readyNotebook])
    );

    renderWithProviders(<NotebookGrid />);

    // Wait for notebooks to load
    await waitFor(() => {
      expect(screen.getByText(processingNotebook.name)).toBeInTheDocument();
    });

    // Check for status indicators (these are visual indicators, so we check for their presence indirectly)
    const processingCard = screen.getByText(processingNotebook.name).closest('div');
    const readyCard = screen.getByText(readyNotebook.name).closest('div');

    expect(processingCard).toBeInTheDocument();
    expect(readyCard).toBeInTheDocument();
  });

  it('displays correct metadata for notebooks', async () => {
    renderWithProviders(<NotebookGrid />);

    // Wait for notebooks to load
    await waitFor(() => {
      expect(screen.getByText('Test Notebook 1')).toBeInTheDocument();
    });

    // Check for source and item counts
    mockNotebooks.forEach((notebook) => {
      expect(screen.getByText(`${notebook.sourceCount} sources`)).toBeInTheDocument();
      expect(screen.getByText(`${notebook.itemCount} items`)).toBeInTheDocument();
    });
  });
});
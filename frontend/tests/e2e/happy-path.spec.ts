import { test, expect } from '@playwright/test';

// Use mocked API responses so we do not hit real Gemini API or database during E2E.
test.describe('InvoiceAI Happy Path', () => {
  test('Upload, view list, and view detail', async ({ page }) => {
    // 1. Mock API Health
    await page.route('**/api/v1/health', async route => {
      await route.fulfill({ json: { status: 'healthy', database: 'connected' } });
    });

    // 2. Mock Invoice List
    await page.route('**/api/v1/invoices*', async route => {
      const url = new URL(route.request().url());
      
      // If it's fetching specific statuses for dashboard KPIs
      if (url.searchParams.get('status')) {
        await route.fulfill({
          json: { items: [], total: 0, page: 1, limit: 1 }
        });
        return;
      }

      // Default list
      await route.fulfill({
        json: {
          items: [
            {
              id: 'test_inv_1',
              file_name: 'test-invoice.pdf',
              vendor_name: 'E2E Vendor',
              invoice_number: 'E2E-001',
              invoice_date: '2023-10-01',
              total: 100.5,
              status: 'PROCESSED',
              created_at: new Date().toISOString()
            }
          ],
          total: 1,
          page: 1,
          limit: 20
        }
      });
    });

    // 3. Mock Upload
    await page.route('**/api/v1/invoices/upload', async route => {
      await route.fulfill({
        status: 201,
        json: {
          id: 'test_inv_2',
          file_name: 'new-upload.pdf',
          status: 'PENDING'
        }
      });
    });

    // 4. Mock Invoice Detail
    await page.route('**/api/v1/invoices/test_inv_2', async route => {
      await route.fulfill({
        json: {
          id: 'test_inv_2',
          file_name: 'new-upload.pdf',
          status: 'PROCESSED',
          vendor_name: 'New Vendor',
          total: 250.00,
          confidence_score: 0.98,
          line_items: [
            { id: '1', description: 'Web Design', quantity: 1, unit_price: 250.00, amount: 250.00 }
          ],
          logs: []
        }
      });
    });
    
    // Mock Invoice File (iframe)
    await page.route('**/api/v1/invoices/test_inv_2/file', async route => {
      await route.fulfill({
        contentType: 'application/pdf',
        body: 'dummy pdf content'
      });
    });

    // Start E2E Test Steps
    
    // Step 1: Open Dashboard
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

    // Step 2: Go to Upload
    await page.getByRole('link', { name: 'Upload New Invoice' }).click();
    await expect(page.getByRole('heading', { name: 'Upload Invoice' })).toBeVisible();

    // Step 3: Select invoice file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'new-upload.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('dummy pdf content')
    });

    // Step 4: Upload
    await page.getByRole('button', { name: 'Upload Invoice' }).click();
    await expect(page.getByText('Upload Successful')).toBeVisible();
    
    // Step 5: Open invoice detail
    await page.getByRole('link', { name: 'View Document Details' }).click();
    
    // Step 6: Verify invoice information
    await expect(page.getByRole('heading', { name: 'new-upload.pdf' })).toBeVisible();
    await expect(page.getByText('Processed')).toBeVisible();
    await expect(page.locator('input[name="vendor_name"]')).toHaveValue('New Vendor');
    await expect(page.locator('input[name="total"]')).toHaveValue('250');
    await expect(page.getByText('Web Design')).toBeVisible();
  });
});

import { test, expect } from '@playwright/test';

test.describe('InvoiceAI Review Flow E2E', () => {
  test('Edit and approve a NEEDS_REVIEW invoice', async ({ page }) => {
    // 1. Mock Invoice Detail
    await page.route('**/api/v1/invoices/test_inv_review', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          json: {
            id: 'test_inv_review',
            file_name: 'review.pdf',
            status: 'NEEDS_REVIEW',
            review_reason: 'Total amount mismatch',
            vendor_name: 'Unknown Vendor',
            total: 100.00,
            confidence_score: 0.70,
            line_items: [],
            logs: []
          }
        });
      } else if (route.request().method() === 'PATCH') {
        const data = JSON.parse(route.request().postData() || '{}');
        await route.fulfill({
          json: {
            id: 'test_inv_review',
            file_name: 'review.pdf',
            status: 'PROCESSED',
            vendor_name: data.vendor_name || 'Unknown Vendor',
            total: data.total || 100.00,
            confidence_score: 0.90,
            line_items: [],
            logs: []
          }
        });
      }
    });
    
    await page.route('**/api/v1/invoices/test_inv_review/file', async route => {
      await route.fulfill({ contentType: 'application/pdf', body: 'dummy pdf content' });
    });

    // Step 1: Open detail page
    await page.goto('/invoices/test_inv_review');
    
    // Step 2: Verify NEEDS_REVIEW state
    await expect(page.getByText('Needs Review')).toBeVisible();
    await expect(page.getByText('Validation Issue')).toBeVisible();
    await expect(page.getByText('Total amount mismatch')).toBeVisible();
    
    // Step 3: Edit vendor
    const vendorInput = page.locator('input[name="vendor_name"]');
    await vendorInput.fill('Corrected Vendor');
    
    // Step 4: Submit
    await page.getByRole('button', { name: 'Approve & Sync' }).click();
    
    // Step 5: Verify backend response success
    await expect(page.getByText('Synced successfully')).toBeVisible();
    
    // The UI should reflect the new state returned from PATCH (which we mocked as PROCESSED)
    await expect(page.locator('input[name="vendor_name"]')).toHaveValue('Corrected Vendor');
  });
});

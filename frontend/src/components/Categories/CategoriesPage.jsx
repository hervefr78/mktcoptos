import { useCallback, useEffect, useMemo, useState } from 'react';
import { API_ENDPOINTS, apiRequest } from '../../config/api';
import './CategoriesPage.css';

const CategoriesPage = () => {
  const [categories, setCategories] = useState([]);
  const [newCategory, setNewCategory] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [deletingId, setDeletingId] = useState(null);

  const loadCategories = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiRequest(API_ENDPOINTS.CATEGORIES);
      setCategories(Array.isArray(data?.categories) ? data.categories : []);
      setError('');
    } catch (err) {
      console.error('Failed to load categories', err);
      setError('Unable to load categories right now.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCategories();
  }, [loadCategories]);

  const handleAdd = async (e) => {
    e.preventDefault();
    const trimmed = newCategory.trim();
    if (!trimmed) return;

    setSaving(true);
    try {
      const data = await apiRequest(API_ENDPOINTS.CATEGORIES, {
        method: 'POST',
        body: JSON.stringify({ name: trimmed }),
      });
      setCategories(Array.isArray(data?.categories) ? data.categories : []);
      setNewCategory('');
      setError('');
    } catch (err) {
      console.error('Failed to add category', err);
      const detail = err?.data?.detail || 'Unable to add category. Please try again.';
      setError(detail);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    setDeletingId(id);
    try {
      const data = await apiRequest(API_ENDPOINTS.CATEGORY(id), { method: 'DELETE' });
      setCategories(Array.isArray(data?.categories) ? data.categories : []);
      setError('');
    } catch (err) {
      console.error('Failed to delete category', err);
      const detail = err?.data?.detail || 'Unable to delete category. Please try again.';
      setError(detail);
    } finally {
      setDeletingId(null);
    }
  };

  const totals = useMemo(
    () => ({ count: categories.length }),
    [categories.length]
  );

  return (
    <div className="categories-page">
      <div className="page-header">
        <div>
          <h1>Categories</h1>
          <p className="page-subtitle">
            Create and manage shared categories for campaigns and generated content.
          </p>
        </div>
        <div className="badge-pill">
          <span className="dot" aria-hidden />
          {totals.count} categories
        </div>
      </div>

      <div className="categories-grid">
        <section className="card add-card">
          <header>
            <div>
              <p className="eyebrow">Add category</p>
              <h3>Capture a new category</h3>
              <p className="muted">Categories keep campaigns and content aligned.</p>
            </div>
          </header>
          <form className="add-form" onSubmit={handleAdd}>
            <label className="form-label" htmlFor="new-category">Category name</label>
            <div className="input-row">
              <input
                id="new-category"
                type="text"
                value={newCategory}
                maxLength={255}
                placeholder="e.g. Product Launches"
                onChange={(e) => setNewCategory(e.target.value)}
                disabled={saving}
              />
              <button type="submit" className="btn-primary" disabled={saving || !newCategory.trim()}>
                {saving ? 'Adding…' : 'Add'}
              </button>
            </div>
            <p className="helper-text">Categories are shared across campaigns and content creation.</p>
          </form>
        </section>

        <section className="card list-card">
          <header>
            <div>
              <p className="eyebrow">Category library</p>
              <h3>All categories</h3>
              <p className="muted">Use these everywhere you select a category.</p>
            </div>
            <button className="ghost" onClick={loadCategories} disabled={loading}>
              ↻ Refresh
            </button>
          </header>

          {error && <div className="alert error">{error}</div>}

          {loading ? (
            <div className="loading">Loading categories…</div>
          ) : categories.length === 0 ? (
            <div className="empty-state">
              <p className="eyebrow">No categories yet</p>
              <p className="muted">Add your first category to start organizing campaigns.</p>
            </div>
          ) : (
            <ul className="category-list">
              {categories.map((category) => (
                <li key={category.id} className="category-row">
                  <div>
                    <p className="category-name">{category.name}</p>
                    <p className="muted">Shared across campaigns and content</p>
                  </div>
                  <button
                    className="ghost danger"
                    onClick={() => handleDelete(category.id)}
                    disabled={deletingId === category.id}
                  >
                    {deletingId === category.id ? 'Removing…' : 'Delete'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
};

export default CategoriesPage;

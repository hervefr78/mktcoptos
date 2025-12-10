import React, { useEffect, useMemo, useState, useRef } from 'react';
import { API_ENDPOINTS } from '../../config/api';
import './CampaignModal.css';

const CampaignModal = ({
  isOpen,
  onClose,
  onSave,
  initialData = {},
  categoryOptions = [],
  modelOptions = [],
}) => {
  const [availableCategories, setAvailableCategories] = useState([]);
  const [formState, setFormState] = useState({
    name: '',
    description: '',
    categoryId: '',
    model: '',
    campaign_type: 'standalone',
    default_language: 'auto',
  });
  const [categoriesLoading, setCategoriesLoading] = useState(false);
  const [categoryError, setCategoryError] = useState(null);
  const [newCategory, setNewCategory] = useState('');
  const [addingCategory, setAddingCategory] = useState(false);

  // Track last initialized data to prevent infinite loops
  const lastInitializedIdRef = useRef(null);

  const effectiveCategories = useMemo(() => {
    const source = availableCategories.length ? availableCategories : categoryOptions;
    return source
      .map((option, index) => {
        if (typeof option === 'string') {
          return { id: option, name: option };
        }
        if (option && typeof option === 'object') {
          const id = option.id ?? option.value ?? index;
          const name = option.name ?? option.label ?? option.value ?? `Category ${index + 1}`;
          return { id, name };
        }
        return null;
      })
      .filter(Boolean);
  }, [availableCategories, categoryOptions]);

  useEffect(() => {
    if (!isOpen) return undefined;

    const controller = new AbortController();
    const loadCategories = async () => {
      setCategoriesLoading(true);
      try {
        const response = await fetch(API_ENDPOINTS.CATEGORIES, { signal: controller.signal });
        if (!response.ok) {
          throw new Error('Failed to load categories');
        }
        const data = await response.json();
        const fetched = Array.isArray(data?.categories) ? data.categories : [];
        setAvailableCategories(fetched);
        setCategoryError(null);
      } catch (err) {
        if (err.name === 'AbortError') return;
        console.error('Failed to load categories', err);
        setAvailableCategories(categoryOptions);
        setCategoryError('Unable to load categories. You can add one below.');
      } finally {
        setCategoriesLoading(false);
      }
    };

    loadCategories();

    return () => controller.abort();
  }, [isOpen, categoryOptions]);

  useEffect(() => {
    if (isOpen) {
      const currentId = initialData?.id || null;

      // Only initialize form when modal opens or data changes
      if (lastInitializedIdRef.current !== currentId) {
        const [firstCategory] = effectiveCategories;
        setFormState({
          name: initialData?.name || '',
          description: initialData?.description || '',
          categoryId: initialData?.category_id ?? initialData?.category ?? firstCategory?.id ?? '',
          model: initialData?.model || modelOptions[0]?.value || modelOptions[0] || '',
          campaign_type: initialData?.campaign_type || 'standalone',
          default_language: initialData?.default_language || 'auto',
        });
        lastInitializedIdRef.current = currentId;
      }
    } else {
      // Reset when modal closes
      lastInitializedIdRef.current = null;
    }
  }, [isOpen, initialData, modelOptions]);

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormState((prev) => ({ ...prev, [name]: value }));
  };

  const canSave =
    effectiveCategories.length > 0 && formState.name.trim().length > 0 && formState.categoryId;

  const handleAddCategory = async (e) => {
    e.preventDefault();
    const trimmed = newCategory.trim();
    if (!trimmed) return;

    setAddingCategory(true);
    try {
      const response = await fetch(API_ENDPOINTS.CATEGORIES, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmed }),
      });
      if (!response.ok) {
        throw new Error('Failed to create category');
      }

      const data = await response.json();
      const updatedCategories = Array.isArray(data?.categories) ? data.categories : [];
      setAvailableCategories(updatedCategories);
      const matched = updatedCategories.find(
        (cat) => (cat.name || cat.label || cat.value || '').toLowerCase() === trimmed.toLowerCase()
      );
      setFormState((prev) => ({ ...prev, categoryId: matched?.id ?? prev.categoryId }));
      setNewCategory('');
      setCategoryError(null);
    } catch (err) {
      console.error('Unable to create category', err);
      setCategoryError('Unable to add category. Please try again.');
    } finally {
      setAddingCategory(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const selectedCategory = effectiveCategories.find(
      (cat) => String(cat.id) === String(formState.categoryId)
    );
    const categoryIdValue = selectedCategory?.id;

    onSave?.({
      ...formState,
      category_id: typeof categoryIdValue === 'number' ? categoryIdValue : Number(categoryIdValue) || categoryIdValue,
      category: selectedCategory?.name,
    });
    onClose?.();
  };

  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal__header">
          <h2>{initialData?.id ? 'Edit Campaign' : 'New Campaign'}</h2>
          <button className="modal__close" onClick={onClose} aria-label="Close modal">
            ×
          </button>
        </div>
        <form className="modal__body" onSubmit={handleSubmit}>
          <label className="modal__label">
            Name
            <input
              name="name"
              value={formState.name}
              onChange={handleChange}
              placeholder="Spring product launch"
              required
            />
          </label>
          <label className="modal__label">
            Description
            <textarea
              name="description"
              value={formState.description}
              onChange={handleChange}
              placeholder="Goals, target audience, and content focus"
              rows={3}
            />
          </label>
          <label className="modal__label">
            Campaign Type
            <select name="campaign_type" value={formState.campaign_type} onChange={handleChange}>
              <option value="standalone">Stand-Alone Project</option>
              <option value="integrated">Integrated Campaign (Multiple Linked Projects)</option>
            </select>
            <p className="modal__helper">
              {formState.campaign_type === 'standalone'
                ? 'Single independent project with its own content and settings'
                : 'Multiple linked projects sharing tone and source content'}
            </p>
          </label>
          <label className="modal__label">
            Category
            <select
              name="categoryId"
              value={formState.categoryId}
              onChange={handleChange}
              disabled={categoriesLoading || effectiveCategories.length === 0}
            >
              {categoriesLoading && <option value="">Loading categories...</option>}
              {!categoriesLoading && effectiveCategories.length === 0 && (
                <option value="">Add a category to continue</option>
              )}
              {effectiveCategories.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                </option>
              ))}
            </select>
          </label>
          <form className="modal__inline-form" onSubmit={handleAddCategory}>
            <div className="inline-input-group">
              <input
                type="text"
                name="newCategory"
                placeholder="Add a new category"
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
              />
              <button type="submit" className="modal__tertiary" disabled={addingCategory}>
                {addingCategory ? 'Adding...' : 'Add Category'}
              </button>
            </div>
            {categoryError && <p className="modal__helper error-text">{categoryError}</p>}
          </form>
          <label className="modal__label">
            Model
            <select name="model" value={formState.model} onChange={handleChange}>
              {modelOptions.length === 0 && <option value="">No models available</option>}
              {modelOptions.map((option) => (
                <option key={option.value || option} value={option.value || option}>
                  {option.label || option}
                </option>
              ))}
            </select>
          </label>
          <div className="modal__footer">
            <button type="button" className="modal__secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="modal__primary" disabled={!canSave}>
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CampaignModal;

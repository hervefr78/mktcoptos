import React from 'react';
import PropTypes from 'prop-types';

const FilterChips = ({ label, options, selected, onChange, multi = false }) => (
  <div className="filter-group">
    <span className="filter-label">{label}</span>
    <div className="chip-row" role="list">
      {options.map((option) => {
        const isSelected = multi ? selected.includes(option) : selected === option;
        return (
          <button
            key={option}
            type="button"
            className={`chip ${isSelected ? 'active' : ''}`}
            onClick={() => onChange(option)}
            role="listitem"
          >
            {option}
          </button>
        );
      })}
    </div>
  </div>
);

FilterChips.propTypes = {
  label: PropTypes.string.isRequired,
  options: PropTypes.arrayOf(PropTypes.string).isRequired,
  selected: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.arrayOf(PropTypes.string),
  ]).isRequired,
  onChange: PropTypes.func.isRequired,
  multi: PropTypes.bool,
};

export default FilterChips;

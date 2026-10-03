// Helper text and per-field validation errors shown under a form input.

export const FieldHint = ({ id, children }) => (
  <p id={id} className="field-hint">{children}</p>
);

export const FieldErrors = ({ id, errors }) =>
  errors?.length ? (
    <ul id={id} className="field-errors" role="alert">
      {errors.map((e) => <li key={e}>{e}</li>)}
    </ul>
  ) : null;

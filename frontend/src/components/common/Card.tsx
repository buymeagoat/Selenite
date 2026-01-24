import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLElement> {
  as?: React.ElementType;
}

export const Card: React.FC<CardProps> = ({ as: Tag = 'section', className = '', ...props }) => {
  const classes = `bg-white border border-sage-mid rounded-lg p-6 w-full min-w-0 max-w-full overflow-x-hidden ${className}`.trim();
  return <Tag className={classes} {...props} />;
};

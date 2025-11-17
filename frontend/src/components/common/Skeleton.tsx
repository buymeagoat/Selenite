import React from 'react';

export const SkeletonCard: React.FC = () => {
  return (
    <div className="bg-white border border-sage-mid rounded-lg p-4 animate-pulse-slow">
      <div className="flex items-start justify-between mb-3">
        <div className="h-4 bg-sage-mid rounded w-3/4"></div>
        <div className="h-6 bg-sage-mid rounded-full w-20"></div>
      </div>
      <div className="space-y-2 mb-4">
        <div className="h-3 bg-sage-mid rounded w-1/2"></div>
        <div className="h-3 bg-sage-mid rounded w-1/3"></div>
      </div>
      <div className="flex gap-2">
        <div className="h-6 bg-sage-mid rounded-full w-16"></div>
        <div className="h-6 bg-sage-mid rounded-full w-20"></div>
      </div>
    </div>
  );
};

export const SkeletonGrid: React.FC = () => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {[1, 2, 3, 4, 5, 6].map(i => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
};

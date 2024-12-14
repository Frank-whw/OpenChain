'use client'

import React, { useState } from 'react'
import { SearchBar } from './SearchBar'
import { SearchButtons } from '@/components/search-buttons'

interface HeaderProps {
  onSubmit: (platform: string, what: string, name: string) => void
}

export default function Header({ onSubmit }: HeaderProps) {
  const [searchParams, setSearchParams] = useState({
    platform: 'github',
    type: 'user',
    name: '',
    find_count: 10
  });

  const handleSearch = (params: {
    platform: string;
    type: string;
    name: string;
    find_count: number;
  }) => {
    setSearchParams(params);
  };

  const handleFindUser = () => {
    if (searchParams.name) {
      onSubmit(searchParams.platform, 'user', searchParams.name);
    }
  };

  const handleFindRepo = () => {
    if (searchParams.name) {
      onSubmit(searchParams.platform, 'repo', searchParams.name);
    }
  };

  return (
    <header className="w-full p-6 bg-white shadow-md">
      <div className="max-w-4xl mx-auto">
        <div className="flex flex-col sm:flex-row items-center gap-4">
          <SearchBar onSearch={handleSearch} />
          <SearchButtons onFindUser={handleFindUser} onFindRepo={handleFindRepo} />
        </div>
      </div>
    </header>
  );
} 
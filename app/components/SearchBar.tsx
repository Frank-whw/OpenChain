import { useState, useCallback } from 'react';
import { Input } from '@/app/components/ui/input';
import { useDebounce } from '@/app/hooks/useDebounce';

interface SearchBarProps {
  onSearch: (params: {
    platform: string;
    type: string;
    name: string;
    find_count: number;
  }) => void;
  isLoading?: boolean;
}

export function SearchBar({ onSearch, isLoading }: SearchBarProps) {
  const [searchText, setSearchText] = useState('');

  const debouncedSearch = useDebounce((value: string) => {
    if (value.trim()) {
      onSearch({
        platform: 'github',
        type: 'user',
        name: value.trim(),
        find_count: 5
      });
    }
  }, 500);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchText(value);
    debouncedSearch(value);
  }, [debouncedSearch]);

  return (
    <div className="w-full max-w-2xl relative">
      <Input
        type="text"
        placeholder="输入用户名或仓库名 (用户名/仓库名)"
        value={searchText}
        onChange={handleInputChange}
        className="w-full h-10 px-4 text-base border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        disabled={isLoading}
      />
      {isLoading && (
        <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500" />
        </div>
      )}
    </div>
  );
} 
import { useState } from 'react';
import { Input } from '@/app/components/ui/input';

interface SearchBarProps {
  onSearch: (params: {
    platform: string;
    type: string;
    name: string;
    find_count: number;
  }) => void;
}

export function SearchBar({ onSearch }: SearchBarProps) {
  const [searchText, setSearchText] = useState('');

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchText(value);
    onSearch({
      platform: 'github',
      type: 'user',
      name: value.trim(),
      find_count: 10
    });
  };

  return (
    <div className="w-full max-w-2xl">
      <Input
        type="text"
        placeholder="输入用户名或仓库名 (用户名/仓库名)"
        value={searchText}
        onChange={handleInputChange}
        className="w-full h-10 px-4 text-base border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      />
    </div>
  );
} 
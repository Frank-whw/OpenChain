import React from 'react'
import { Button } from './ui/button'

interface SearchButtonsProps {
  onFindUser: () => void
  onFindRepo: () => void
}

export function SearchButtons({ onFindUser, onFindRepo }: SearchButtonsProps) {
  return (
    <div className="flex space-x-4">
      <Button 
        onClick={onFindUser}
        className="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded-full shadow-lg transition duration-300 ease-in-out transform hover:scale-105"
      >
        Find User
      </Button>
      <Button 
        onClick={onFindRepo}
        className="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded-full shadow-lg transition duration-300 ease-in-out transform hover:scale-105"
      >
        Find Repo
      </Button>
    </div>
  )
}


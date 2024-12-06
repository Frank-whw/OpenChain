import React from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'


const MyComponent = () => {
  return (
    <div>
      <Label htmlFor="myInput">My Input:</Label>
      <Input id="myInput" type="text" placeholder="Enter text" />
      <Button>Submit</Button>
    </div>
  )
}

export default MyComponent


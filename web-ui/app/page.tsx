
import { getProjects } from '@/lib/server-api'
import { HomeClient } from '@/components/home-client'

export default async function Home() {
  const initialProjects = await getProjects()

  return <HomeClient initialProjects={initialProjects} />
}

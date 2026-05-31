import { useAppContext } from '../context/AppContext';

export function useRecommendation() {
  const { recommendations, slots, answer } = useAppContext();
  return { recommendations, slots, answer };
}

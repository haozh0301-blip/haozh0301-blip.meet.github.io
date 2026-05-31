import { Link, NavLink } from 'react-router-dom';

function Header() {
  return (
    <header className="site-header">
      <Link to="/" className="site-header__brand">
        Meet
      </Link>
      <nav className="site-header__nav">
        <NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : undefined)}>
          首页
        </NavLink>
        <NavLink to="/recommend" className={({ isActive }) => (isActive ? 'active' : undefined)}>
          推荐详情
        </NavLink>
      </nav>
    </header>
  );
}

export default Header;

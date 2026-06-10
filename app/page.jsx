'use client';
import { useState, useEffect } from 'react';

export default function Home() {
  const [usuario, setUsuario] = useState(null);
  
  if (!usuario) {
    return (
      <div style={{maxWidth: '360px', margin: '80px auto', background: '#fff', padding: '36px', borderRadius: '10px', textAlign: 'center'}}>
        <h1>📄 Gerador de Assuntos</h1>
        <form onSubmit={(e) => {
          e.preventDefault();
          const email = e.target.email.value;
          const senha = e.target.senha.value;
          if (email === 'admin@local' && senha === 'admin123') {
            setUsuario({nome: 'Admin', papel: 'ADMIN'});
          } else {
            alert('Erro!');
          }
        }}>
          <input type="email" placeholder="E-mail" required style={{width: '100%', padding: '8px', margin: '10px 0'}} />
          <input type="password" placeholder="Senha" required style={{width: '100%', padding: '8px', margin: '10px 0'}} />
          <button type="submit" style={{width: '100%', padding: '12px', background: '#1d4e89', color: '#fff', border: 'none', borderRadius: '5px'}}>Entrar</button>
        </form>
        <p style={{color: '#666', fontSize: '12px'}}>admin@local / admin123</p>
      </div>
    );
  }

  return (
    <div style={{padding: '20px'}}>
      <h1>Bem-vindo, {usuario.nome}!</h1>
      <button onClick={() => setUsuario(null)}>Sair</button>
    </div>
  );
}

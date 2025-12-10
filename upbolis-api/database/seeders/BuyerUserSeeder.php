<?php

namespace Database\Seeders;

use App\Models\User;
use App\Models\Wallet;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

class BuyerUserSeeder extends Seeder
{
    public function run(): void
    {
        $buyer = User::firstOrCreate(
            ['email' => 'buyer@upbolis.com'],
            [
                'name'     => 'Buyer UPBolis',
                'password' => Hash::make('Buyer1234'),
                'role'     => 'buyer',
            ]
        );

        Wallet::firstOrCreate(
            ['user_id' => $buyer->id],
            ['balance' => 0]
        );
    }
}
